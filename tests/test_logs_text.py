import random
import unittest
from datetime import date, datetime

from tests import oracles
from treppenwitz import analyse
from treppenwitz.keywords import rake
from treppenwitz.logs import BURST_MIN, find_bursts, parse_log, parse_ts, template_of
from treppenwitz.summary import sentences, summarise
from treppenwitz.synthetic import make_document

TODAY = date(2026, 11, 20)


class TestLogLines(unittest.TestCase):
    def test_levels_and_formats(self):
        cases = {
            "2026-11-20 10:15:03 ERROR db down": ("error", datetime(2026, 11, 20, 10, 15, 3)),
            "2026-11-20T10:15:03.123Z WARN slow": ("warning", datetime(2026, 11, 20, 10, 15, 3)),
            "2026-11-20 10:15 [CRITICAL] x": ("fatal", datetime(2026, 11, 20, 10, 15)),
            "20.11.2026 10:15:03 Fehler: Datenbank": ("error", datetime(2026, 11, 20, 10, 15, 3)),
            "[INFO] started": ("info", None),
            "DEBUG cache warm": ("debug", None),
            "Warnung: Speicher knapp": ("warning", None),
            "2026-11-20 10:15:03 - fatal - out of memory": ("fatal", datetime(2026, 11, 20, 10, 15, 3)),
        }
        for line, (level, ts) in cases.items():
            e = parse_log(line, 1)
            self.assertIsNotNone(e, line)
            self.assertEqual((e.level, e.ts), (level, ts), line)

    def test_a_sentence_that_starts_with_a_level_word_is_not_a_log_entry(self):
        for line in ("Info zum Termin folgt", "Warnung vor dem Umbau bleibt bestehen"):
            self.assertIsNone(parse_log(line, 1), line)

    def test_level_free_error_words_are_inferred_and_marked(self):
        e = parse_log("Server Fehler erkannt", 2)
        self.assertEqual((e.level, e.inferred), ("error", True))
        self.assertEqual(parse_log("The job failed overnight", 1).level, "error")

    def test_negated_error_words_are_not_errors(self):
        for line in ("Kein Fehler gefunden", "Läuft ohne Fehler", "no error seen", "This is not an error"):
            self.assertIsNone(parse_log(line, 1), line)

    def test_timestamp_edge_cases(self):
        self.assertIsNone(parse_ts("2026-13-40 10:00:00"))
        self.assertEqual(parse_ts("2026-11-20 10:15:03+02:00"), datetime(2026, 11, 20, 10, 15, 3))

    def test_templates_mask_variable_parts(self):
        self.assertEqual(template_of("user 42 failed login from 10.0.3.77"), "user <n> failed login from <ip>")
        self.assertEqual(template_of("cache miss 0xDEADBEEF"), "cache miss <hex>")
        self.assertEqual(template_of("id 3f2b8c1e-aaaa-bbbb-cccc-0123456789ab gone"), "id <id> gone")
        self.assertEqual(template_of("Waited 1,5 s"), "waited <n> s")
        self.assertEqual(template_of("A  B"), template_of("a b"))


class TestBursts(unittest.TestCase):
    def entries(self, per_minute, quiet_minutes=0):
        out, n = [], 1
        for minute, count in per_minute.items():
            for s in range(count):
                out.append(parse_log(f"2026-11-20 10:{minute:02d}:{s:02d} ERROR x{s}", n))
                n += 1
        if quiet_minutes:
            out.append(parse_log(f"2026-11-20 10:{quiet_minutes:02d}:00 INFO fine", n))
        return out

    def test_a_cluster_against_a_quiet_log(self):
        b = find_bursts(self.entries({10: 1, 30: 9}, quiet_minutes=59))
        self.assertEqual([(x.minute.minute, x.count) for x in b], [(30, 9)])

    def test_steady_errors_are_not_a_burst(self):
        self.assertEqual(find_bursts(self.entries(dict.fromkeys(range(10, 20), 6))), [])

    def test_below_the_floor_is_never_a_burst(self):
        self.assertEqual(find_bursts(self.entries({10: BURST_MIN - 1}, quiet_minutes=50)), [])

    def test_typical_is_the_median_over_the_whole_span_including_silent_minutes(self):
        ents = self.entries({10: 2, 11: 2, 12: 2, 40: 7})
        b = find_bursts(ents)
        counts = [2, 2, 2, 7]
        self.assertEqual(b[0].typical, oracles.brute_force_median_with_zeros(counts, 31))

    def test_no_timestamps_no_bursts(self):
        self.assertEqual(find_bursts([parse_log("ERROR boom", 1)] * 10), [])

    def test_generated_documents(self):
        rng = random.Random(11)
        hit = false_alarm = 0
        for i in range(200):
            burst = i % 2 == 0
            text, truth = make_document(rng, TODAY, n_logs=30, burst=burst)
            a = analyse(text, TODAY)
            if burst:
                hit += [b.minute for b in a.bursts] == truth.burst_minutes
            else:
                false_alarm += bool(a.bursts)
        self.assertEqual((hit, false_alarm), (100, 0))

    def test_levels_and_templates_match_the_generator(self):
        rng = random.Random(12)
        for _ in range(100):
            text, truth = make_document(rng, TODAY, burst=True)
            a = analyse(text, TODAY)
            got = {e.line: e.level for e in a.entries}
            self.assertEqual(got, {k: ("fatal" if v == "critical" else v) for k, v in truth.levels.items()})
            self.assertEqual({e.template for e in a.entries} - set(oracles.TEMPLATES), set())
            self.assertEqual(sum(n for _, n, _ in analyse(text, TODAY, templates=99).templates), len(truth.levels))


class TestKeywords(unittest.TestCase):
    def test_hand_worked_example(self):
        # "rote" and "gruene" each occur once with degree 2, "aepfel" twice with degree 2+2: every word scores 2, both phrases 4.
        got = rake(["Rote Aepfel und gruene Aepfel"])
        self.assertEqual([(p, int(s)) for p, s in got], [("gruene Aepfel", 4), ("Rote Aepfel", 4)])

    def test_agrees_with_an_independent_implementation(self):
        words = ["server", "backup", "datenbank", "kunde", "bericht", "migration", "lizenz", "zertifikat", "monitoring", "vertrag"]
        glue = ["und", "der", "die", ",", ".", "mit"]
        rng = random.Random(3)
        for _ in range(100):
            lines = [" ".join(rng.choice(words + glue) for _ in range(rng.randint(3, 15))) for _ in range(rng.randint(1, 6))]
            ours = [(p.lower(), s) for p, s in rake(lines, 8)]
            self.assertEqual(ours, oracles.rake(lines, 8), lines)

    def test_no_phrase_starts_or_ends_with_a_stopword(self):
        for p, _ in rake(["Der Server und die Datenbank sind mit dem Backup verbunden."], 20):
            self.assertNotIn(p.split()[0].lower(), {"der", "die", "und", "mit"})
            self.assertNotIn(p.split()[-1].lower(), {"der", "die", "und", "mit"})

    def test_empty_and_symbols(self):
        self.assertEqual(rake([]), [])
        self.assertEqual(rake(["!!! ??? 123 ..."]), [])

    def test_display_form_keeps_umlauts_and_case(self):
        self.assertEqual(rake(["Kundendaten prüfen"])[0][0], "Kundendaten prüfen")


class TestSummary(unittest.TestCase):
    NOTES = [(1, "Die Datenbank wurde migriert. Die Migration der Datenbank lief ohne Probleme."), (2, "Kaffee ist alle."),
             (4, "Der Kunde fragt nach dem Stand der Datenbank Migration. Das Wetter ist schön heute, finde ich.")]

    def test_sentences_are_verbatim_and_in_order(self):
        s = summarise(self.NOTES, 2)
        self.assertEqual(len(s), 2)
        self.assertEqual([x.line for x in s], sorted(x.line for x in s))
        by_line = dict(self.NOTES)
        for x in s:
            self.assertIn(x.text, by_line[x.line])

    def test_short_fragments_are_not_sentences(self):
        self.assertNotIn("Kaffee ist alle.", [s.text for s in sentences(self.NOTES)])

    def test_the_sentence_about_the_repeated_topic_wins(self):
        top = summarise(self.NOTES, 1)[0]
        self.assertIn("Datenbank", top.text)

    def test_k_larger_than_available_and_empty(self):
        self.assertEqual(len(summarise(self.NOTES, 50)), len(sentences(self.NOTES)))
        self.assertEqual(summarise([], 3), [])

    def test_whole_document_summary_is_verbatim(self):
        rng = random.Random(5)
        for _ in range(100):
            text, _ = make_document(rng, TODAY)
            lines = text.split("\n")
            for s in analyse(text, TODAY).summary:
                self.assertIn(s.text, lines[s.line - 1])


if __name__ == "__main__":
    unittest.main()
