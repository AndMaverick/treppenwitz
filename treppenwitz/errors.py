"""One error type for input the tool cannot use, so the command line can exit 2 on it."""
from __future__ import annotations


class TextError(ValueError):
    """The input, an option or a date could not be used."""
