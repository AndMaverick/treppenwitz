"""Key terms by RAKE (Rose et al. 2010): candidate phrases are runs of words between stopwords and punctuation; a word scores
degree/frequency, a phrase scores the sum of its words. Exact Fractions, so ranking never depends on float rounding."""
from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction

from .lang import STOP_DE, STOP_EN, fold

_TOKEN = re.compile(r"(?:[\w\-]+\.){2,}[^\W\d_]{2,}|[^\W\d_]+(?:['\-][^\W\d_]+)*|[^\w\s]|\d+|_")
_WORDLIKE = re.compile(r"[^\W\d_]")
STOP = STOP_DE | STOP_EN
MARKERS = frozenset(["todo", "aufgabe", "task", "fixme", "action", "notiz", "note", "info", "debug", "warn", "warning", "warnung", "trace", "offen", "erledigt", "done", "fertig"])
MAX_WORDS = 4
MIN_LEN = 3


def candidates(lines: list[str]) -> list[list[tuple[str, str]]]:
    """Candidate phrases as lists of (folded, as written) words, one list per phrase occurrence."""
    out: list[list[tuple[str, str]]] = []
    for line in lines:
        cur: list[tuple[str, str]] = []
        for tok in _TOKEN.findall(line):
            f = fold(tok)
            if not _WORDLIKE.match(tok) or "." in tok or f in STOP or f in MARKERS or len(f) < MIN_LEN:
                if cur:
                    out.append(cur)
                cur = []
            else:
                cur.append((f, tok))
                if len(cur) == MAX_WORDS:
                    out.append(cur)
                    cur = []
        if cur:
            out.append(cur)
    return out


def rake(lines: list[str], top: int = 8) -> list[tuple[str, Fraction]]:
    phrases = candidates(lines)
    freq: Counter[str] = Counter()
    degree: Counter[str] = Counter()
    shown: dict[str, str] = {}
    for p in phrases:
        shown.setdefault(" ".join(f for f, _ in p), " ".join(t for _, t in p))
        for w, _ in p:
            freq[w] += 1
            degree[w] += len(p)
    word_score = {w: Fraction(degree[w], freq[w]) for w in freq}
    seen: dict[str, tuple[Fraction, int]] = {}
    for p in phrases:
        key = " ".join(f for f, _ in p)
        score = sum((word_score[f] for f, _ in p), Fraction(0))
        n = seen[key][1] + 1 if key in seen else 1
        seen[key] = (score, n)
    ranked = sorted(seen.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))
    return [(shown[k], v[0]) for k, v in ranked[:top]]
