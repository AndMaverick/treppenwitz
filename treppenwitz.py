# treppenwitz.py
# Automatisierte Textzusammenfassung für Logs, Aufgaben und Notizen

import sys
from collections import Counter

def analysiere_text(dateiname):
    try:
        with open(dateiname, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print("⚠️ Datei nicht gefunden!")
        return

    woerter = text.split()
    anzahl_aufgaben = text.lower().count("todo") + text.lower().count("aufgabe")
    haeufigste_woerter = Counter(woerter).most_common(4)

    print("📊 Analyse-Ergebnisse")
    print(f"📝 Aufgaben gefunden: {anzahl_aufgaben}")
    print(f"🔑 Wichtige Begriffe: {[wort for wort, _ in haeufigste_woerter]}")
    print("🚨 Priorität: Hoch" if "Fehler" in text else "✅ Priorität: Normal")
    print("➡️ Nächste Schritte: Backup überprüfen, Server neu starten\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("⚠️ Nutzung: python treppenwitz.py beispiel.txt")
    else:
        analysiere_text(sys.argv[1])

