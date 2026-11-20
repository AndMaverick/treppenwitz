"""Log lines: timestamp and level parsing, message templates (numbers, ids and addresses masked) and error bursts."""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import datetime

from .lang import fold

_TS = (r"(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
       r"|\d{2}\.\d{2}\.\d{4}[ ,]+\d{2}:\d{2}(?::\d{2})?)")
_LEVELS = r"fatal|critical|crit|error|err|fehler|warning|warn|warnung|info|debug|trace"
_LINE = re.compile(rf"^\s*(?:(?P<ts>{_TS})\s*[|\-]?\s*)?(?:\[(?P<l1>{_LEVELS})\]|(?P<l2>{_LEVELS})\b(?P<colon>\s*:)?)\s*[|\-]?\s*(?P<msg>.*)$", re.IGNORECASE)
_ISO_TS = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?")
_DE_TS = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})[ ,]+(\d{2}):(\d{2})(?::(\d{2}))?")
_LEVEL_OF = {"fatal": "fatal", "critical": "fatal", "crit": "fatal", "error": "error", "err": "error", "fehler": "error",
             "warning": "warning", "warn": "warning", "warnung": "warning", "info": "info", "debug": "debug", "trace": "debug"}
_SIGNAL = re.compile(r"\b(?:fehler|error|exception|traceback|crash|abgestuerzt|fehlgeschlagen|failed|failure)\b")
_NEGATORS = {"kein", "keine", "keinen", "keiner", "ohne", "no", "without", "not", "nicht", "never", "nie"}
_MASKS = [(re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<id>"),
          (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<ip>"),
          (re.compile(r"\b0x[0-9a-f]+\b|\b[0-9a-f]{12,}\b"), "<hex>"),
          (re.compile(r"\d+(?:[.,]\d+)*"), "<n>")]
BURST_MIN = 5
BURST_FACTOR = 3


@dataclass(frozen=True)
class LogEntry:
    line: int
    ts: datetime | None
    level: str                # fatal, error, warning, info, debug
    message: str
    template: str
    inferred: bool = False    # the level was guessed from a word such as "Fehler" in a line without a level


@dataclass(frozen=True)
class Burst:
    minute: datetime
    count: int
    typical: float            # median errors per minute over the whole span of the log, minutes with none included


def parse_ts(raw: str) -> datetime | None:
    """Timestamps are read as written; a time zone suffix is ignored."""
    m = _ISO_TS.match(raw)
    try:
        if m:
            y, mo, d, h, mi, s = m.groups()
            return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
        m = _DE_TS.match(raw)
        if m:
            d, mo, y, h, mi, s = m.groups()
            return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
    except ValueError:
        return None
    return None


def template_of(message: str) -> str:
    t = fold(message)
    for rx, sub in _MASKS:
        t = rx.sub(sub, t)
    return " ".join(t.split())


def _negated(folded: str, start: int) -> bool:
    before = re.findall(r"[a-z]+", folded[:start])[-2:]
    return any(w in _NEGATORS for w in before)


def parse_log(line: str, number: int) -> LogEntry | None:
    m = _LINE.match(line)
    if m:
        bare = m["l2"] is not None
        if not bare or m["ts"] or m["colon"] or m["l2"].isupper():
            level = _LEVEL_OF[(m["l1"] or m["l2"]).lower()]
            msg = m["msg"].strip()
            return LogEntry(number, parse_ts(m["ts"]) if m["ts"] else None, level, msg, template_of(msg))
    low = fold(line)
    for s in _SIGNAL.finditer(low):
        if not _negated(low, s.start()):
            msg = line.strip()
            return LogEntry(number, None, "error", msg, template_of(msg), inferred=True)
    return None


def _median_with_zeros(counts: list[int], total: int) -> float:
    zeros = total - len(counts)
    return float(statistics.median([0] * zeros + sorted(counts)))


def find_bursts(entries: list[LogEntry]) -> list[Burst]:
    """Minutes with at least BURST_MIN errors and at least BURST_FACTOR times the typical (median) number of errors per minute."""
    stamped = [e.ts.replace(second=0, microsecond=0) for e in entries if e.ts]
    if not stamped:
        return []
    first, last = min(stamped), max(stamped)
    total = int((last - first).total_seconds() // 60) + 1
    per: dict[datetime, int] = {}
    for e in entries:
        if e.ts and e.level in ("error", "fatal"):
            k = e.ts.replace(second=0, microsecond=0)
            per[k] = per.get(k, 0) + 1
    typical = _median_with_zeros(list(per.values()), total)
    return [Burst(k, n, typical) for k, n in sorted(per.items()) if n >= BURST_MIN and n >= BURST_FACTOR * max(typical, 1.0)]
