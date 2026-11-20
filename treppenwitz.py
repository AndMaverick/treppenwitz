# treppenwitz.py
# Launcher: kept so that "python treppenwitz.py beispiel.txt" still works. The code lives in the treppenwitz/ package.
# Treppenwitz: Textanalyse für Logs, Aufgaben und Notizen.

import sys

from treppenwitz.cli import main
from treppenwitz.legacy import analysiere_text  # noqa: F401  (the original function name, still importable from here)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Nutzung: python treppenwitz.py beispiel.txt")
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
