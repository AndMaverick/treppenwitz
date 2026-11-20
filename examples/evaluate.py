"""Measured claims for the README. Every number is recomputed here; the script exits 1 if a check fails.

Run:  python examples/evaluate.py
"""
from __future__ import annotations

import random
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import oracles  # noqa: E402
from treppenwitz import analyse  # noqa: E402
from treppenwitz.dates import find_dates  # noqa: E402
from treppenwitz.synthetic import make_document  # noqa: E402
from treppenwitz.tasks import parse_task  # noqa: E402

TODAY = date(2026, 11, 20)

# Lines written the way people write them, not the way the generator does. (line, what a careful reader would say)
HARD_TASKS = [
    ("TODO: Backup prüfen", True), ("- [ ] Rechnung senden", True), ("- [x] Rechnung senden", True), ("Aufgabe: Bericht", True),
    ("FIXME: Zeitzone falsch", True), ("Task force meeting at noon", False), ("Die Aufgabe war schwer", False), ("Aufgaben sind verteilt", False),
    ("Todo-Liste aktualisiert", False), ("Aufgabe 3: Bericht schreiben", True), ("TODO bericht", True), ("todo bericht", True),
    ("* [ ] Vertrag", True), ("1. Vertrag unterschreiben", True), ("Bitte Vertrag unterschreiben", True),
]

KNOWN_MISSES = {"todo bericht", "1. Vertrag unterschreiben", "Bitte Vertrag unterschreiben"}


def main() -> int:
    ok = True
    rng = random.Random(2026)

    # 1. Dates: every day for four years, four spellings.
    total = hit = 0
    for d in oracles.all_days(date(2024, 1, 1), date(2027, 12, 31)):
        for s in oracles.date_styles(d):
            total += 1
            hit += find_dates(f"bis {s} bitte", TODAY) == [d]
    print(f"dates found exactly: {hit}/{total}")
    ok &= hit == total

    # 2. Generated documents with known answers.
    n = 2000
    fields = lines_ok = 0
    levels = bursts = false_alarms = 0
    overdue_ok = owner_ok = notes_clean = 0
    burst_docs = 0
    for i in range(n):
        burst = i % 2 == 0
        text, truth = make_document(rng, TODAY, burst=burst)
        raw = text.split("\n")
        a = analyse(text, TODAY, language="en")
        got = {t.line: t for t in a.tasks}
        lines_ok += set(got) == {t["line"] for t in truth.tasks}
        fields += all(
            (got[t["line"]].done, got[t["line"]].high, got[t["line"]].owner, got[t["line"]].due) == (t["done"], t["high"], t["owner"], t["due"])
            for t in truth.tasks if t["line"] in got
        )
        levels += {e.line: e.level for e in a.entries} == {k: ("fatal" if v == "critical" else v) for k, v in truth.levels.items()}
        if burst:
            burst_docs += 1
            bursts += [b.minute for b in a.bursts] == truth.burst_minutes
        else:
            false_alarms += bool(a.bursts)
        by = {x.code: x for x in a.advice}
        open_ = [t for t in truth.tasks if not t["done"]]
        want_over = [t["line"] for t in open_ if t["due"] and t["due"] < TODAY][:5]
        overdue_ok += list(by["overdue"].lines if "overdue" in by else []) == want_over
        want_owner = [t["line"] for t in open_ if t["high"] and not t["owner"]][:5]
        owner_ok += list(by["owner"].lines if "owner" in by else []) == want_owner
        notes_clean += all(parse_task(raw[k - 1], k, TODAY) is None for k in truth.notes)
    print(f"generated documents: {n}")
    print(f"  task lines found exactly: {lines_ok}/{n}; done, priority, owner and due date right on every task: {fields}/{n}")
    print(f"  log levels right on every line: {levels}/{n}")
    print(f"  error bursts found at the right minute: {bursts}/{burst_docs}; false alarms in {n - burst_docs} quiet documents: {false_alarms}")
    print(f"  overdue advice cites exactly the overdue tasks: {overdue_ok}/{n}; unowned-priority advice: {owner_ok}/{n}; notes mistaken for tasks: {n - notes_clean}")
    ok &= all(x == n for x in (lines_ok, fields, levels, overdue_ok, owner_ok, notes_clean)) and bursts == burst_docs and false_alarms == 0

    # 3. Summaries are quotations: every sentence is a substring of its line.
    quoted = checked = 0
    for _ in range(300):
        text, _ = make_document(rng, TODAY)
        raw = text.split("\n")
        for s in analyse(text, TODAY).summary:
            checked += 1
            quoted += s.text in raw[s.line - 1]
    print(f"summary sentences found verbatim in the input: {quoted}/{checked}")
    ok &= quoted == checked

    # 4. Determinism across hash seeds.
    outs = set()
    for seed in ("0", "7", "4242"):
        r = subprocess.run([sys.executable, "-m", "treppenwitz", str(ROOT / "examples" / "wochenbericht.txt"), "--json", "--today", "2026-11-20"],
                           capture_output=True, cwd=ROOT, env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}, timeout=60)
        outs.add(r.stdout)
    print(f"identical output over 3 hash seeds: {len(outs) == 1}")
    ok &= len(outs) == 1

    # 5. Honest limits: lines written the way people do, scored against what a careful reader says.
    right = [(line, want) for line, want in HARD_TASKS if (parse_task(line, 1, TODAY) is not None) == want]
    wrong = [(line, want) for line, want in HARD_TASKS if (line, want) not in right]
    print(f"hand-written task lines classified as a careful reader would: {len(right)}/{len(HARD_TASKS)}")
    for line, want in wrong:
        print(f"  missed: {line!r} (is {'a task' if want else 'not a task'})")
    ok &= {line for line, _ in wrong} == KNOWN_MISSES      # the shortfall is documented in the README; any other change is a regression or a fix to record
    print("pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
