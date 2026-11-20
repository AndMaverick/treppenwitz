import random
import unittest
from datetime import date

from tests import oracles
from treppenwitz.dates import find_dates
from treppenwitz.synthetic import make_document
from treppenwitz.tasks import parse_task

TODAY = date(2026, 11, 20)


class TestDates(unittest.TestCase):
    def test_every_day_of_four_years_in_four_spellings(self):
        for d in oracles.all_days(date(2024, 1, 1), date(2027, 12, 31)):
            for s in oracles.date_styles(d):
                self.assertEqual(find_dates(f"bis {s} bitte", TODAY), [d], s)

    def test_no_year_takes_the_year_of_today(self):
        self.assertEqual(find_dates("bis 25.11. fertig", TODAY), [date(2026, 11, 25)])
        self.assertEqual(find_dates("due Dec 3", TODAY), [date(2026, 12, 3)])
        self.assertEqual(find_dates("am 3 Dez", date(2030, 1, 1)), [date(2030, 12, 3)])

    def test_impossible_dates_are_skipped_not_repaired(self):
        for s in ("31.02.2026", "2026-13-01", "2026-02-30", "29.02.2026", "0.5.2026", "32.1.2026", "31. Februar 2026"):
            self.assertEqual(find_dates(s, TODAY), [], s)
        self.assertEqual(find_dates("29.02.2028", TODAY), [date(2028, 2, 29)])

    def test_versions_and_addresses_are_not_dates(self):
        for s in ("version 1.2.3 released", "host 10.0.1.5", "build 2.11.4-beta", "Kapitel 3.1.2 beachten"):
            self.assertEqual(find_dates(s, TODAY), [], s)

    def test_two_digit_year_and_month_names(self):
        self.assertEqual(find_dates("20.11.26", TODAY), [date(2026, 11, 20)])
        self.assertEqual(find_dates("3. März 2027", TODAY), [date(2027, 3, 3)])
        self.assertEqual(find_dates("Mar 3rd, 2027", TODAY), [date(2027, 3, 3)])
        self.assertEqual(find_dates("1 May 2027", TODAY), [date(2027, 5, 1)])

    def test_a_month_and_year_alone_is_not_a_day(self):
        self.assertEqual(find_dates("Mai 2026 war ruhig", TODAY), [])

    def test_several_dates_come_back_in_order(self):
        self.assertEqual(find_dates("von 2026-12-01 bis 05.12.2026", TODAY), [date(2026, 12, 1), date(2026, 12, 5)])


class TestTaskLines(unittest.TestCase):
    def t(self, line):
        return parse_task(line, 1, TODAY)

    def test_marker_forms(self):
        for line in ("TODO: a", "todo: a", "Aufgabe: a", "TODO a", "- [ ] a", "* [ ] a", "[ ] a", "FIXME: a", "Task - a", "- TODO: a"):
            self.assertIsNotNone(self.t(line), line)

    def test_ordinary_sentences_are_not_tasks(self):
        for line in ("Task force meeting at noon", "Aufgaben sind verteilt", "Die Aufgabe war schwer", "Todo-Liste aktualisiert", "Done and dusted.",
                     "Offene Punkte folgen", "2026-11-20 10:00:00 ERROR x", "[ERROR] boom", "Notiz: etwas", ""):
            self.assertIsNone(self.t(line), line)

    def test_done_state(self):
        self.assertTrue(self.t("- [x] a").done)
        self.assertTrue(self.t("- [X] a").done)
        self.assertFalse(self.t("- [ ] a").done)
        self.assertTrue(self.t("ERLEDIGT: a").done)
        self.assertTrue(self.t("Aufgabe: a (erledigt)").done)
        self.assertTrue(self.t("TODO: a ✓").done)
        self.assertFalse(self.t("TODO: erledigt wird das nie").done)

    def test_priority_owner_due(self):
        t = self.t("TODO: Server patchen !! @anna bis 25.11.")
        self.assertEqual((t.high, t.owner, t.due), (True, "anna", date(2026, 11, 25)))
        t = self.t("- [ ] ship it (P0) owner: ben due 2026-12-01")
        self.assertEqual((t.high, t.owner, t.due), (True, "ben", date(2026, 12, 1)))
        t = self.t("TODO: mail an a@b.de schicken")
        self.assertIsNone(t.owner)
        t = self.t("TODO: Rechnung dringend senden")
        self.assertTrue(t.high)
        t = self.t("TODO: Release am 25.11. vorbereiten")
        self.assertIsNone(t.due)                    # a date without a "bis/due/by" is not a deadline

    def test_a_date_in_the_task_text_that_is_impossible_gives_no_due(self):
        self.assertIsNone(self.t("TODO: x bis 31.02.2026").due)

    def test_agreement_with_the_generator_truth(self):
        rng = random.Random(7)
        for _ in range(300):
            text, truth = make_document(rng, TODAY)
            lines = text.split("\n")
            for tr in truth.tasks:
                got = parse_task(lines[tr["line"] - 1], tr["line"], TODAY)
                self.assertIsNotNone(got, lines[tr["line"] - 1])
                self.assertEqual((got.done, got.high, got.owner, got.due), (tr["done"], tr["high"], tr["owner"], tr["due"]), lines[tr["line"] - 1])
            for n in truth.notes:
                self.assertIsNone(parse_task(lines[n - 1], n, TODAY), lines[n - 1])


if __name__ == "__main__":
    unittest.main()
