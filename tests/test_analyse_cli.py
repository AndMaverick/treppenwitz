import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from datetime import date, timedelta
from pathlib import Path

from treppenwitz import analyse
from treppenwitz.cli import main
from treppenwitz.synthetic import make_document

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 11, 20)
EM = chr(0x2014)


def run(*argv, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdin
    if stdin is not None:
        sys.stdin = io.TextIOWrapper(io.BytesIO(stdin), encoding="utf-8")
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(argv))
            except SystemExit as e:
                code = int(e.code or 0)
    finally:
        sys.stdin = old
    return code, out.getvalue(), err.getvalue()


class TestAdviceAgainstTruth(unittest.TestCase):
    def test_overdue_soon_owner_undated_match_the_generator(self):
        rng = random.Random(21)
        for _ in range(300):
            text, truth = make_document(rng, TODAY, burst=rng.random() < 0.5)
            a = analyse(text, TODAY, language="en")
            by = {x.code: x for x in a.advice}
            open_ = [t for t in truth.tasks if not t["done"]]
            exp = {
                "overdue": [t["line"] for t in open_ if t["due"] and t["due"] < TODAY],
                "soon": [t["line"] for t in open_ if t["due"] and TODAY <= t["due"] <= TODAY + timedelta(days=3)],
                "owner": [t["line"] for t in open_ if t["high"] and not t["owner"]],
                "undated": [t["line"] for t in open_ if not t["due"]],
            }
            for code, lines in exp.items():
                if lines:
                    self.assertEqual(list(by[code].lines), lines[:5], code)
                    self.assertIn(f"{len(lines)}", by[code].text("en"))
                else:
                    self.assertNotIn(code, by)
            n_err = sum(v in ("error", "critical") for v in truth.levels.values())
            self.assertEqual(("errors" in by), n_err > 0)

    def test_priority(self):
        self.assertEqual(analyse("TODO: a bis 2026-12-31", TODAY).priority, "normal")
        self.assertEqual(analyse("TODO: a !!", TODAY).priority, "high")
        self.assertEqual(analyse("TODO: a bis 2026-01-01", TODAY).priority, "high")
        self.assertEqual(analyse("2026-11-20 10:00:00 ERROR x", TODAY).priority, "high")
        self.assertEqual(analyse("2026-11-20 10:00:00 INFO x", TODAY).priority, "normal")

    def test_clear_when_nothing_is_wrong(self):
        a = analyse("- [x] fertig\n2026-11-20 10:00:00 INFO ok\n", TODAY)
        self.assertEqual([x.code for x in a.advice], ["clear"])

    def test_every_advice_item_names_real_lines(self):
        rng = random.Random(22)
        for _ in range(100):
            text, _ = make_document(rng, TODAY, burst=True)
            n = len(text.split("\n")) - 1
            for x in analyse(text, TODAY).advice:
                self.assertTrue(all(1 <= i <= n for i in x.lines))

    def test_messages_exist_in_both_languages(self):
        from treppenwitz.lang import MESSAGES
        self.assertEqual(set(MESSAGES["de"]), set(MESSAGES["en"]))
        rng = random.Random(23)
        text, _ = make_document(rng, TODAY, burst=True)
        a = analyse(text, TODAY)
        for x in a.advice:
            self.assertTrue(x.text("de") and x.text("en"))

    def test_the_old_fixed_next_steps_line_is_gone(self):
        text = (ROOT / "beispiel.txt").read_text(encoding="utf-8")
        report = run(str(ROOT / "beispiel.txt"), "--today", "2026-11-20")[1]
        self.assertNotIn("Server neu starten", report)
        self.assertIn("Server Fehler erkannt", report)
        self.assertTrue(text)


class TestRobustness(unittest.TestCase):
    def test_crlf_bom_and_normalisation_do_not_change_the_result(self):
        rng = random.Random(31)
        for _ in range(50):
            text, _ = make_document(rng, TODAY, burst=True)
            base = analyse(text, TODAY)
            for variant in (text.replace("\n", "\r\n"), "﻿" + text, unicodedata.normalize("NFD", text)):
                v = analyse(variant, TODAY)
                self.assertEqual(v, base)

    def test_random_unicode_never_raises(self):
        rng = random.Random(32)
        pool = [chr(c) for c in list(range(32, 127)) + list(range(0xC0, 0x250)) + [0x2014, 0x4E2D, 0x1F600, 0x0E01, 0x0301, 0x200B, 9, 10, 13]]
        for _ in range(500):
            text = "".join(rng.choice(pool) for _ in range(rng.randint(0, 400)))
            a = analyse(text, TODAY)
            self.assertEqual(a.sha256, analyse(text, TODAY).sha256)

    def test_empty_input(self):
        a = analyse("", TODAY)
        self.assertEqual((a.line_count, a.tasks, a.entries, a.keywords, a.summary), (0, (), (), (), ()))
        self.assertEqual([x.code for x in a.advice], ["clear"])

    def test_language_detection(self):
        self.assertEqual(analyse("Der Server ist nicht erreichbar und die Datenbank wurde neu gestartet.", TODAY).language, "de")
        self.assertEqual(analyse("The server is not reachable and the database was restarted by the team.", TODAY).language, "en")
        self.assertEqual(analyse("ok", TODAY).language, "unknown")


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.sample = self.write("a.txt", "TODO: Backup prüfen bis 2026-11-01 @anna\nServer Fehler erkannt\n2026-11-20 10:00:00 ERROR db down\n")

    def write(self, name, data):
        p = self.dir / name
        p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        return str(p)

    def test_json_equals_the_library(self):
        code, out, _ = run(self.sample, "--json", "--today", "2026-11-20", "--lang", "en")
        self.assertEqual(code, 0)
        data = json.loads(out)[self.sample]
        a = analyse(Path(self.sample).read_text(encoding="utf-8"), TODAY)
        self.assertEqual(data["sha256"], a.sha256)
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["owner"], "anna")
        self.assertEqual(data["log"]["errors"], 2)
        self.assertEqual(data["log"]["inferred_errors"], 1)
        self.assertIn("overdue", [x["code"] for x in data["advice"]])

    def test_markdown_and_text(self):
        _, md, _ = run(self.sample, "--markdown", "--today", "2026-11-20", "--lang", "en")
        self.assertTrue(md.startswith("# Analysis"))
        self.assertIn("- [ ] Backup prüfen", md)
        _, de, _ = run(self.sample, "--today", "2026-11-20", "--lang", "de")
        self.assertIn("Nächste Schritte", de)

    def test_stdin(self):
        code, out, _ = run("-", "--json", "--today", "2026-11-20", stdin=b"TODO: x\n")
        self.assertEqual((code, len(json.loads(out)["-"]["tasks"])), (0, 1))

    def test_exit_codes(self):
        self.assertEqual(run(str(self.dir / "none.txt"))[0], 2)
        self.assertEqual(run(self.write("bad.txt", b"\xff\xfe\x00"))[0], 2)
        self.assertEqual(run(self.sample, "--today", "20.11.2026")[0], 2)
        self.assertEqual(run(self.sample, "--today", "2026-11-20")[0], 0)
        self.assertEqual(run(self.sample, "--today", "2026-11-20", "--fail-on", "error")[0], 1)
        self.assertEqual(run(self.sample, "--today", "2026-11-20", "--fail-on", "overdue")[0], 1)
        clean = self.write("clean.txt", "- [x] erledigt\n")
        self.assertEqual(run(clean, "--today", "2026-11-20", "--fail-on", "error", "--fail-on", "overdue", "--fail-on", "high")[0], 0)

    def test_bad_input_prints_nothing_to_stdout(self):
        code, out, err = run(self.sample, str(self.dir / "none.txt"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("cannot read", err)

    def test_no_em_dash_in_any_output(self):
        for args in ([self.sample, "--today", "2026-11-20"], [self.sample, "--markdown"], [self.sample, "--json"], ["--help"]):
            self.assertNotIn(EM, run(*args)[1])

    def test_determinism_across_hash_seeds_and_the_legacy_launcher(self):
        outs = set()
        for seed in ("0", "1", "999"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run([sys.executable, "-m", "treppenwitz", str(ROOT / "beispiel.txt"), "--json", "--today", "2026-11-20"],
                               capture_output=True, env=env, cwd=ROOT, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            outs.add(r.stdout)
        self.assertEqual(len(outs), 1)
        r = subprocess.run([sys.executable, "treppenwitz.py", "beispiel.txt"], capture_output=True, cwd=ROOT, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Server Fehler erkannt", r.stdout.decode("utf-8"))
        r = subprocess.run([sys.executable, "treppenwitz.py"], capture_output=True, cwd=ROOT, timeout=60)
        self.assertEqual(r.returncode, 2)

    def test_legacy_function(self):
        sys.path.insert(0, str(ROOT))
        try:
            from treppenwitz.legacy import analysiere_text
        finally:
            sys.path.pop(0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            analysiere_text(str(ROOT / "beispiel.txt"))
            analysiere_text(str(self.dir / "none.txt"))
        self.assertIn("Aufgaben: 2", out.getvalue())
        self.assertIn("Datei nicht gefunden", out.getvalue())


class TestRepository(unittest.TestCase):
    def test_no_em_dash_anywhere_in_the_repository(self):
        kinds = {".py", ".md", ".txt", ".toml", ".yml"}
        files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in kinds and ".git" not in p.parts and "__pycache__" not in p.parts]
        bad = [str(p.relative_to(ROOT)) for p in files if EM in p.read_text(encoding="utf-8")]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
