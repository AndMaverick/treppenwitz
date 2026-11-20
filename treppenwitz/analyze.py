"""The analysis: one pass over the lines, each classified as a task, a log entry or a note, then keywords, summary and advice."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from . import advice as adv
from .keywords import rake
from .lang import detect_language
from .logs import Burst, LogEntry, find_bursts, parse_log
from .summary import Sentence, summarise
from .tasks import Task, parse_task

_NEWLINE = re.compile(r"\r\n|\r|\n")


@dataclass(frozen=True)
class Analysis:
    sha256: str
    language: str                       # "de", "en" or "unknown"
    line_count: int
    tasks: tuple[Task, ...]
    entries: tuple[LogEntry, ...]
    bursts: tuple[Burst, ...]
    templates: tuple[tuple[str, int, str], ...]       # (template, count, first message)
    keywords: tuple[tuple[str, Fraction], ...]
    summary: tuple[Sentence, ...]
    advice: tuple[adv.Advice, ...]
    priority: str                       # "high" or "normal"
    today: date

    @property
    def report_language(self) -> str:
        return self.language if self.language in ("de", "en") else "de"

    def count(self, level: str) -> int:
        return sum(e.level == level for e in self.entries)


def normalise(text: str) -> str:
    """NFC, no byte order mark and \\n line ends, so the same notes give the same result and the same hash however they were saved."""
    return _NEWLINE.sub("\n", unicodedata.normalize("NFC", text.lstrip("\ufeff")))


def analyse(text: str, today: date | None = None, language: str | None = None, top: int = 8, sentences: int = 3, templates: int = 5) -> Analysis:
    text = normalise(text)
    today = today or date.today()
    lines = _NEWLINE.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    tasks: list[Task] = []
    entries: list[LogEntry] = []
    notes: list[tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        t = parse_task(line, i, today)
        if t:
            tasks.append(t)
            continue
        e = parse_log(line, i)
        if e:
            entries.append(e)
        else:
            notes.append((i, line))
    lang = language or detect_language(text)
    bursts = find_bursts(entries)
    first: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for e in entries:
        counts[e.template] += 1
        first.setdefault(e.template, e.message)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:templates]
    kw = rake([n for _, n in notes] + [t.text for t in tasks], top)
    notices = adv.advise(tasks, entries, bursts, today)
    high = (any(e.level in ("error", "fatal") for e in entries) or bool(adv.unowned_high(tasks)) or bool(adv.overdue(tasks, today))
            or any(t.high and not t.done for t in tasks))
    return Analysis(hashlib.sha256(text.encode("utf-8")).hexdigest(), lang, len(lines), tuple(tasks), tuple(entries), tuple(bursts),
                    tuple((k, n, first[k]) for k, n in ranked), tuple(kw), tuple(summarise(notes, sentences)), tuple(notices),
                    "high" if high else "normal", today)
