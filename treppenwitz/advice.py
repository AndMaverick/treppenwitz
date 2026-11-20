"""Next steps, derived by rule from what was found. Every item says which lines it is about; nothing is a fixed phrase."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from .lang import MESSAGES
from .logs import Burst, LogEntry
from .tasks import Task

SOON_DAYS = 3
MAX_NAMES = 3
MAX_LINES = 5


@dataclass(frozen=True)
class Advice:
    code: str
    params: tuple[tuple[str, str | int], ...]
    lines: tuple[int, ...]

    def text(self, lang: str) -> str:
        return MESSAGES[lang]["a_" + self.code].format(**dict(self.params))

    def to_dict(self, lang: str) -> dict[str, object]:
        return {"code": self.code, "text": self.text(lang), "lines": list(self.lines)}


def _names(tasks: list[Task]) -> str:
    shown = [t.text if len(t.text) <= 40 else t.text[:37] + "..." for t in tasks[:MAX_NAMES]]
    more = len(tasks) - MAX_NAMES
    return "; ".join(shown) + (f" (+{more})" if more > 0 else "")


def is_open(t: Task) -> bool:
    return not t.done


def overdue(tasks: list[Task], today: date) -> list[Task]:
    return [t for t in tasks if is_open(t) and t.due is not None and t.due < today]


def due_soon(tasks: list[Task], today: date) -> list[Task]:
    return [t for t in tasks if is_open(t) and t.due is not None and today <= t.due <= today + timedelta(days=SOON_DAYS)]


def unowned_high(tasks: list[Task]) -> list[Task]:
    return [t for t in tasks if is_open(t) and t.high and t.owner is None]


def advise(tasks: list[Task], entries: list[LogEntry], bursts: list[Burst], today: date) -> list[Advice]:
    out: list[Advice] = []
    fatal = [e for e in entries if e.level == "fatal"]
    errors = [e for e in entries if e.level == "error"]
    if fatal:
        out.append(Advice("fatal", (("n", len(fatal)), ("y", "y" if len(fatal) == 1 else "ies")), tuple(e.line for e in fatal[:MAX_LINES])))
    if errors:
        by = Counter(e.template for e in errors)
        top, c = sorted(by.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        shown = next(e.message for e in errors if e.template == top)
        out.append(Advice("errors", (("n", len(errors)), ("k", len(by)), ("top", shown), ("c", c)), tuple(e.line for e in errors[:MAX_LINES])))
    for b in bursts:
        out.append(Advice("burst", (("when", b.minute.strftime("%Y-%m-%d %H:%M")), ("n", b.count), ("typical", f"{b.typical:g}")),
                          tuple(e.line for e in entries if e.ts and e.ts.replace(second=0, microsecond=0) == b.minute)[:MAX_LINES]))
    for code, found in (("overdue", overdue(tasks, today)), ("soon", due_soon(tasks, today)), ("owner", unowned_high(tasks))):
        if found:
            out.append(Advice(code, (("n", len(found)), ("names", _names(found))), tuple(t.line for t in found[:MAX_LINES])))
    undated = [t for t in tasks if is_open(t) and t.due is None]
    if undated:
        out.append(Advice("undated", (("n", len(undated)),), tuple(t.line for t in undated[:MAX_LINES])))
    if not (fatal or errors or bursts or overdue(tasks, today) or unowned_high(tasks)):
        out.append(Advice("clear", (), ()))
    return out
