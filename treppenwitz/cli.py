"""python -m treppenwitz FILE... : tasks, log entries, key terms, a summary and next steps from notes and logs.

Exit codes: 0 analysed, 1 a --fail-on gate tripped, 2 a file, date or option could not be used."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import advice as adv
from . import report
from ._version import __version__
from .analyze import Analysis, analyse
from .errors import TextError

GATES = ("error", "overdue", "high")


def read(path: str, encoding: str) -> str:
    try:
        raw = sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()
    except OSError as e:
        raise TextError(f"cannot read {path}: {e.strerror or e}") from None
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError as e:
        raise TextError(f"{path} is not valid {encoding} (byte {e.start}); pass --encoding for another one") from None


def parse_today(s: str | None) -> date:
    if s is None:
        return date.today()
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise TextError(f"--today must be a date like 2026-11-20, got {s!r}") from None


def tripped(a: Analysis, gates: list[str]) -> list[str]:
    hits = []
    if "error" in gates and any(e.level in ("error", "fatal") for e in a.entries):
        hits.append("error")
    if "overdue" in gates and adv.overdue(list(a.tasks), a.today):
        hits.append("overdue")
    if "high" in gates and a.priority == "high":
        hits.append("high")
    return hits


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="treppenwitz", description="Tasks, log entries, key terms, a summary and next steps from notes and logs.")
    p.add_argument("files", nargs="+", help="text files, or - for standard input")
    p.add_argument("--version", action="version", version=f"treppenwitz {__version__}")
    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true")
    fmt.add_argument("--markdown", action="store_true")
    p.add_argument("--lang", choices=["de", "en"], help="report language (default: the language of the text, German if unclear)")
    p.add_argument("--today", help="the date that due dates are compared with, YYYY-MM-DD (default: today)")
    p.add_argument("--top", type=int, default=8, help="number of key terms")
    p.add_argument("--encoding", default="utf-8-sig")
    p.add_argument("--fail-on", action="append", choices=GATES, default=[], metavar="GATE", help="exit 1 if the gate trips: " + ", ".join(GATES))
    args = p.parse_args(argv)
    try:
        today = parse_today(args.today)
        results = {f: analyse(read(f, args.encoding), today, top=args.top) for f in args.files}
    except TextError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({f: report.to_dict(a, args.lang) for f, a in results.items()}, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        for f, a in results.items():
            sys.stdout.write((report.as_markdown if args.markdown else report.as_text)(a, args.lang, f if len(results) > 1 else None))
    hits = {f: tripped(a, args.fail_on) for f, a in results.items()}
    for f, h in hits.items():
        if h:
            print(f"gate tripped for {f}: {', '.join(h)}", file=sys.stderr)
    return 1 if any(hits.values()) else 0
