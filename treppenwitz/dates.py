"""Find calendar dates in free text: 2026-11-20, 20.11.2026, 20.11.26, 20.11., 20. November 2026, 20 Nov 2026, Nov 20, 2026.

A date without a year takes the year of ``today``. An impossible date (31.02., 2026-13-01) is skipped, never repaired."""
from __future__ import annotations

import re
from datetime import date

from .lang import MONTH_LOOKUP, fold

_MN = "|".join(sorted((re.escape(n) for n in MONTH_LOOKUP), key=len, reverse=True))
_ISO = re.compile(r"(?<![\d.])(\d{4})-(\d{2})-(\d{2})(?!\d)")
_NUM = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(?:(\d{4}|\d{2})(?!\d)|(?!\d))")
_DMY = re.compile(rf"(?<![\w.])(\d{{1,2}})\.?\s*({_MN})\b\.?(?:\s*,?\s*(\d{{4}})(?!\d))?")
_MDY = re.compile(rf"(?<![\w])({_MN})\b\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:\s*,?\s*(\d{{4}})(?!\d))?")


def _make(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _year(raw: str | None, today: date) -> int:
    if raw is None:
        return today.year
    return int(raw) + 2000 if len(raw) == 2 else int(raw)


def find_dates(text: str, today: date) -> list[date]:
    """Every valid date in ``text``, in order of appearance. Overlapping readings of the same characters count once."""
    s = fold(text)
    found: list[tuple[int, int, date]] = []
    for m in _ISO.finditer(s):
        d = _make(int(m[1]), int(m[2]), int(m[3]))
        if d:
            found.append((m.start(), m.end(), d))
    for m in _NUM.finditer(s):
        d = _make(_year(m[3], today), int(m[2]), int(m[1]))
        if d:
            found.append((m.start(), m.end(), d))
    for m in _DMY.finditer(s):
        d = _make(_year(m[3], today), MONTH_LOOKUP[m[2]], int(m[1]))
        if d:
            found.append((m.start(), m.end(), d))
    for m in _MDY.finditer(s):
        d = _make(_year(m[3], today), MONTH_LOOKUP[m[1]], int(m[2]))
        if d:
            found.append((m.start(), m.end(), d))
    found.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    out: list[date] = []
    last_end = -1
    for start, end, d in found:
        if start >= last_end:
            out.append(d)
            last_end = end
    return out
