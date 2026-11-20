# Treppenwitz

**Automatisierte Textzusammenfassung für Logs, Aufgaben und Notizen.**
Tasks, log entries, key terms, a summary and next steps from plain notes and logs, in German and English. Dependency free Python 3.10+.

[![CI](https://github.com/AndMaverick/treppenwitz/actions/workflows/ci.yml/badge.svg)](https://github.com/AndMaverick/treppenwitz/actions/workflows/ci.yml)

*Treppenwitz* is the clever remark that occurs to you on the way down the stairs, too late. This tool is the opposite: it reads the pile of
notes, TODOs and log lines you already have and tells you, while you are still in the room, what is overdue, what is on fire and what has no owner.

## Use

```
python -m treppenwitz examples/wochenbericht.txt --today 2026-11-20 --lang en
```

```
Analysis
  Language: de   Priority: high
  Tasks: 6 (4 open, 2 done, 1 overdue, 2 high priority)
  Log: 11 entries, 7 errors, 1 warnings
    6x upstream 3 refused connection
    1x cache miss for key 0x9f3a77c1
    1x connection pool at 85 percent
  Key terms: alten Datenbank prüfen, Datenbank antwortet schneller, neuen Cluster einrichten, neuen Cluster, Datenbank gefragt, Kunden versenden, Lizenz verlängern, Team trifft
  Summary:
    (line 3) Die Migration der Datenbank auf den neuen Cluster ist abgeschlossen.
    (line 3) Die Migration lief ohne Datenverlust, die Datenbank antwortet schneller als zuvor.
    (line 4) Der Kunde hat nach dem Stand der Datenbank gefragt und wünscht einen wöchentlichen Bericht über die Migration.
  Next steps:
    - 7 error entries in 2 distinct message(s); most frequent: upstream 3 refused connection (6x) [lines 17, 18, 19, 20, 21]
    - Errors cluster around 2026-11-20 03:12: 6 entries in one minute, against a typical 0 [lines 17, 18, 19, 20, 21]
    - 1 open task(s) are past their due date: Zertifikat für api.example.com erneue... [line 8]
    - 2 high priority task(s) have no owner: Zertifikat für api.example.com erneue...; Lizenz verlängern !! [lines 8, 11]
    - 1 open tasks have no due date [line 11]
```

Every line of the advice says where it comes from (`[lines 17, 18, ...]`), and every summary sentence is a quotation from your text with its line number.
The report is German or English (`--lang`, default: the language of the text).

```
python -m treppenwitz notes.txt --json                    # machine readable, with a SHA-256 of the normalised input
python -m treppenwitz notes.txt --markdown                # a report you can paste into a ticket
python -m treppenwitz notes.txt --fail-on error --fail-on overdue   # exit 1 if the gate trips, for CI or a cron job
cat notes.txt | python -m treppenwitz -                   # standard input
python treppenwitz.py beispiel.txt                        # the original entry point still works
```

Exit codes: `0` analysed, `1` a `--fail-on` gate tripped (`error`, `overdue`, `high`), `2` a file, encoding or `--today` value could not be used
(nothing is printed to stdout then). Use `--today YYYY-MM-DD` to make a report reproducible.

```python
from datetime import date
from treppenwitz import analyse

a = analyse(open("notes.txt", encoding="utf-8").read(), today=date(2026, 11, 20))
a.priority, [t.text for t in a.tasks if not t.done], a.bursts
```

## What it understands

| Input | Recognised as |
|---|---|
| `- [ ] text`, `- [x] text`, `TODO: text`, `Aufgabe: text`, `FIXME - text` | a task; done by `[x]`, `ERLEDIGT:` or a trailing `(erledigt)` |
| `!!`, `(P0)`, `(P1)`, `prio: hoch`, `dringend`, `urgent`, `asap` | high priority |
| `@anna`, `owner: anna`, `verantwortlich: anna` | the owner |
| `bis 25.11.`, `due 2026-12-01`, `deadline: 3. März 2027` | the due date (also `20.11.26`, `Nov 20, 2026`) |
| `2026-11-20 10:15:03 ERROR ...`, `[WARN] ...`, `20.11.2026 10:15 Fehler: ...` | a log entry with level and time |
| `Server Fehler erkannt` (no level) | an error, marked `inferred`; negations (`Kein Fehler`, `ohne Fehler`, `no error`) are not errors |

Impossible dates (`31.02.`) are skipped, never repaired. Version numbers (`1.2.3`) and IP addresses are not dates.

**Error bursts.** Errors are counted per minute. A minute is a burst if it has at least 5 errors and at least 3 times the median errors per minute
over the whole span of the log (minutes with no errors count as zero), so a steady stream of errors is not a burst and a quiet log with one cluster is.

**Messages are grouped by template.** Numbers, IP addresses, hex values and UUIDs are masked, so `user 42 failed login from 10.0.3.77` and
`user 7 failed login from 10.0.9.1` are the same message.

**Key terms** use RAKE (Rose, Engel, Cramer and Cowley, 2010) with exact fractions, so ranking never depends on floating point rounding.
**The summary** is extractive: the sentences whose content words are the most frequent in the text, in their original order.

## Measured

`python examples/evaluate.py` recomputes these from scratch and exits 1 if a check fails. CI runs it.

```
dates found exactly: 5844/5844
generated documents: 2000
  task lines found exactly: 2000/2000; done, priority, owner and due date right on every task: 2000/2000
  log levels right on every line: 2000/2000
  error bursts found at the right minute: 1000/1000; false alarms in 1000 quiet documents: 0
  overdue advice cites exactly the overdue tasks: 2000/2000; unowned-priority advice: 2000/2000; notes mistaken for tasks: 0
summary sentences found verbatim in the input: 805/805
identical output over 3 hash seeds: True
hand-written task lines classified as a careful reader would: 12/15
  missed: 'todo bericht' (is a task)
  missed: '1. Vertrag unterschreiben' (is a task)
  missed: 'Bitte Vertrag unterschreiben' (is a task)
pass
```

The 2000 documents are generated with known answers (`treppenwitz/synthetic.py`) and the checks that compare against them live in
`tests/`, with an independent RAKE implementation and `strftime`-built dates as oracles. 55 tests, ruff and strict mypy run on Python 3.10 to 3.13.

## Honest limits

- **Agreement with the generator is not accuracy on your notes.** The generated documents use the formats listed above, so those figures say the code
  does what it documents. The last block is the real test: 15 handwritten lines, 12 right. The three misses are `todo bericht` (a lowercase
  keyword without a colon is not trusted, because `task force meeting` is not a task), a numbered list item, and an imperative sentence with no marker.
  Unmarked tasks are not found.
- **Inferred errors are guesses.** A free text line containing `Fehler`, `error`, `failed` and similar words is counted as an error (and flagged
  `inferred` in the JSON) unless one of the two words before it is a negation. `Fehler beheben wir morgen` is counted as an error.
- **Time zones are ignored.** Timestamps are compared as written.
- **A date without a year takes the year of `--today`**, so `bis 05.01.` written in December means this January, which is already past.
- **The summary and key terms are statistical.** They need a few sentences to say anything and work on German and English, nothing else.
- **No priority is invented.** A task is high priority only if the text says so.

## Develop

```
python -m unittest discover -s tests -t . -v
ruff check . && mypy
```

MIT. AndMaverick LLC.
