"""Extractive summary: the sentences of the notes that carry the most frequent content words. Sentences come back verbatim, with line numbers."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from .keywords import MARKERS, STOP
from .lang import fold, words

_SPLIT = re.compile(r"(?<=[.!?])\s+")
MIN_WORDS = 4


@dataclass(frozen=True)
class Sentence:
    line: int
    text: str


def sentences(notes: list[tuple[int, str]]) -> list[Sentence]:
    out = []
    for number, line in notes:
        for part in _SPLIT.split(line.strip()):
            if len(words(part)) >= MIN_WORDS:
                out.append(Sentence(number, part))
    return out


def _content(text: str) -> list[str]:
    return [f for f in (fold(w) for w in words(text)) if f not in STOP and f not in MARKERS and len(f) >= 3]


def summarise(notes: list[tuple[int, str]], k: int = 3) -> list[Sentence]:
    """The ``k`` best sentences, in the order they appear. A sentence scores the mean frequency of its content words in the whole text."""
    sents = sentences(notes)
    freq: Counter[str] = Counter()
    for s in sents:
        freq.update(_content(s.text))
    scored = []
    for i, s in enumerate(sents):
        c = _content(s.text)
        scored.append((Fraction(sum(freq[w] for w in c), len(c)) if c else Fraction(0), i))
    best = sorted(scored, key=lambda t: (-t[0], t[1]))[:k]
    return [sents[i] for _, i in sorted(best, key=lambda t: t[1])]
