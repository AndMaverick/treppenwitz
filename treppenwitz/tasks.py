"""Tasks in notes: checkboxes and marker lines (TODO, Aufgabe, task, fixme), with done state, priority, owner and due date."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .dates import find_dates
from .lang import fold

_LINE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:\[(?P<x>[ xX])\]\s*|(?P<kw>todo|to-do|aufgabe|task|fixme|action|offen|erledigt|done|fertig)\b(?P<sep>\s*\d{0,3}\s*:|\s+-\s)?\s*)(?P<rest>.*)$",
    re.IGNORECASE,
)
_DONE_KW = {"erledigt", "done", "fertig"}
_DONE_TAIL = re.compile(r"(?:\((?:erledigt|done|fertig)\)|\[(?:erledigt|done)\]|✓|✔|✅)\s*$")
_HIGH = re.compile(r"!!|\(p[01]\)|\bp[01]\b|\bprio(?:ritaet)?\s*[:=]?\s*(?:hoch|high|1|a)\b|\b(?:dringend|urgent|asap|kritisch|critical|sofort|blocker)\b")
_OWNER_AT = re.compile(r"(?<![\w.@])@(\w[\w.\-]*)")
_OWNER_KW = re.compile(r"\b(?:owner|verantwortlich|zust(?:ä|ae)ndig|assignee)\s*:\s*(\w[\w.\-]*)", re.IGNORECASE)
_DUE_KW = re.compile(r"\b(?:bis|faellig|due|until|by|deadline|spaetestens)\b\s*:?\s*(.*)")


@dataclass(frozen=True)
class Task:
    line: int
    text: str
    done: bool
    high: bool
    owner: str | None
    due: date | None
    marker: str            # "checkbox" or the keyword as written, lower-cased

    def to_dict(self) -> dict[str, object]:
        return {"line": self.line, "text": self.text, "done": self.done, "high_priority": self.high, "owner": self.owner,
                "due": self.due.isoformat() if self.due else None, "marker": self.marker}


def parse_task(line: str, number: int, today: date) -> Task | None:
    """The task on this line, or None. A bare word such as "task force meeting" is not a marker: it needs a colon, dash or capitals."""
    m = _LINE.match(line)
    if not m:
        return None
    kw = m["kw"]
    if kw and not (m["sep"] or kw.isupper()):
        return None
    rest = m["rest"].strip()
    if not rest and not kw:
        return None
    low = fold(rest)
    done = (m["x"] in ("x", "X")) if m["x"] is not None else (kw.lower() in _DONE_KW)
    if _DONE_TAIL.search(low):
        done = True
    owner_m = _OWNER_AT.search(rest) or _OWNER_KW.search(rest)
    due = None
    dm = _DUE_KW.search(low)
    if dm:
        ds = find_dates(dm[1], today)
        due = ds[0] if ds else None
    return Task(number, rest, done, bool(_HIGH.search(low)), owner_m[1] if owner_m else None, due, "checkbox" if kw is None else kw.lower())
