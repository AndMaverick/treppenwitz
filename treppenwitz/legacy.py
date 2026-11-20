"""The original entry point, kept: ``analysiere_text(dateiname)`` prints the report in German."""
from __future__ import annotations

import sys

from . import report
from .analyze import analyse


def analysiere_text(dateiname: str) -> None:
    try:
        with open(dateiname, encoding="utf-8-sig") as f:
            text = f.read()
    except FileNotFoundError:
        print("Datei nicht gefunden!")
        return
    sys.stdout.write(report.as_text(analyse(text), "de"))
