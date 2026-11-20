"""Synthetic notes with known answers, for the tests and the verification script. Every document comes with the truth it was built from."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .lang import MONTHS

NAMES = ["anna", "ben", "chris", "dana", "emil"]
THINGS_DE = ["Backup prüfen", "Bericht aktualisieren", "Server neu starten", "Kundendaten synchronisieren", "Rechnung versenden", "Lizenz verlängern",
             "Zertifikat erneuern", "Monitoring einrichten", "Datenbank migrieren", "Vertrag unterschreiben"]
NOTES = ["Das Team trifft sich jeden Montag zur Planung.", "Die Migration der Datenbank läuft seit zwei Wochen ohne Probleme.",
         "Der Kunde wünscht einen wöchentlichen Bericht über die Datenbank.", "Die Planung der Migration wird im Team abgestimmt."]
LOG_MESSAGES = ["connection to db{n} timed out after {ms} ms", "user {n} failed login from 10.0.{n}.{m}", "cache miss for key 0x{h}", "disk usage at {n} percent"]


@dataclass
class Truth:
    tasks: list[dict[str, object]] = field(default_factory=list)       # line, done, high, owner, due
    levels: dict[int, str] = field(default_factory=dict)               # line -> level
    template_counts: dict[str, int] = field(default_factory=dict)
    burst_minutes: list[datetime] = field(default_factory=list)
    notes: list[int] = field(default_factory=list)


def _date_text(d: date, style: int) -> str:
    if style == 0:
        return d.isoformat()
    if style == 1:
        return d.strftime("%d.%m.%Y")
    if style == 2:
        return d.strftime("%d.%m.%y")
    mon = MONTHS[d.month][0].capitalize() if d.month != 3 else "März"
    return f"{d.day}. {mon} {d.year}"


def make_document(rng: random.Random, today: date, n_tasks: int = 8, n_logs: int = 20, burst: bool = False) -> tuple[str, Truth]:
    lines: list[str] = []
    truth = Truth()
    items: list[tuple[str, object]] = []
    for _ in range(n_tasks):
        items.append(("task", None))
    for _ in range(rng.randint(2, 4)):
        items.append(("note", rng.choice(NOTES)))
    rng.shuffle(items)
    for kind, payload in items:
        number = len(lines) + 1
        if kind == "note":
            lines.append(str(payload))
            truth.notes.append(number)
            continue
        text = rng.choice(THINGS_DE)
        done, high = rng.random() < 0.3, rng.random() < 0.3
        owner = rng.choice(NAMES) if rng.random() < 0.5 else None
        due = today + timedelta(days=rng.randint(-20, 30)) if rng.random() < 0.6 else None
        style = rng.randrange(4)
        body = text + (" !!" if high else "") + (f" @{owner}" if owner else "") + (f" bis {_date_text(due, rng.randrange(4))}" if due else "")
        form = rng.randrange(3)
        if form == 0:
            line = f"- [{'x' if done else ' '}] {body}"
        elif form == 1:
            line = f"{'ERLEDIGT' if done else 'TODO'}: {body}"
        else:
            line = f"Aufgabe: {body}" + (" (erledigt)" if done else "")
        del style
        lines.append(line)
        truth.tasks.append({"line": number, "done": done, "high": high, "owner": owner, "due": due})
    t = datetime(today.year, today.month, today.day, 8, 0, 0)
    for _ in range(n_logs):
        t += timedelta(seconds=rng.randint(20, 400))
        level = rng.choices(["info", "warning", "error", "debug"], [5, 2, 2, 2])[0]
        msg = rng.choice(LOG_MESSAGES).format(n=rng.randint(1, 999), m=rng.randint(1, 250), ms=rng.randint(10, 5000), h=f"{rng.randrange(16**8):08x}")
        lines.append(f"{t:%Y-%m-%d %H:%M:%S} {level.upper()} {msg}")
        truth.levels[len(lines)] = level
    if burst:
        t += timedelta(minutes=30)
        start = t.replace(second=0)
        truth.burst_minutes.append(start)
        for i in range(8):
            lines.append(f"{start + timedelta(seconds=5 * i):%Y-%m-%d %H:%M:%S} ERROR upstream {rng.randint(1, 9)} refused connection")
            truth.levels[len(lines)] = "error"
    return "\n".join(lines) + "\n", truth
