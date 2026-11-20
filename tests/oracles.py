"""Independent checks: they derive expectations from the generator's truth or from the standard library, not from treppenwitz's code."""
from __future__ import annotations

import itertools
import re
from datetime import date, timedelta
from fractions import Fraction

STOP = {"und", "der", "die", "das", "the", "and", "of", "a", "ist", "in", "mit"}
TEMPLATES = ["connection to db<n> timed out after <n> ms", "user <n> failed login from <ip>", "cache miss for key <hex>", "disk usage at <n> percent",
             "upstream <n> refused connection"]


def date_styles(d: date) -> list[str]:
    """Four spellings of a date made with strftime, plus the German month name written out."""
    months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return [d.strftime("%Y-%m-%d"), d.strftime("%d.%m.%Y"), d.strftime("%d.%m.%y"), f"{d.day}. {months[d.month - 1]} {d.year}"]


def all_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def rake(phrases_text: list[str], top: int = 8) -> list[tuple[str, Fraction]]:
    """RAKE written the long way: split on stopwords and punctuation, score by degree over frequency (min word length 3, max 4 words)."""
    phrases: list[list[str]] = []
    for line in phrases_text:
        cur: list[str] = []
        for tok in re.findall(r"\w[\w'\-]*|[^\w\s]", line.lower()):
            if re.fullmatch(r"[^\W\d_][\w'\-]*", tok) and tok not in STOP and len(tok) >= 3:
                cur.append(tok)
                if len(cur) == 4:
                    phrases.append(cur)
                    cur = []
            else:
                if cur:
                    phrases.append(cur)
                cur = []
        if cur:
            phrases.append(cur)
    freq: dict[str, int] = {}
    deg: dict[str, int] = {}
    for p in phrases:
        for w in p:
            freq[w] = freq.get(w, 0) + 1
            deg[w] = deg.get(w, 0) + len(p)
    scores: dict[str, tuple[Fraction, int]] = {}
    for p in phrases:
        k = " ".join(p)
        sc = sum((Fraction(deg[w], freq[w]) for w in p), Fraction(0))
        scores[k] = (sc, scores.get(k, (sc, 0))[1] + 1)
    return [(k, v[0]) for k, v in sorted(scores.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))[:top]]


def brute_force_median_with_zeros(counts: list[int], total_minutes: int) -> float:
    xs = sorted(counts + [0] * (total_minutes - len(counts)))
    n = len(xs)
    return float(xs[n // 2]) if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def pairs(xs):
    return itertools.combinations(xs, 2)
