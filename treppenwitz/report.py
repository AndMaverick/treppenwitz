"""Reports: plain text (German or English), Markdown and JSON, all from the same Analysis."""
from __future__ import annotations

import json
from typing import Any

from . import advice as adv
from ._version import __version__
from .analyze import Analysis
from .lang import MESSAGES


def to_dict(a: Analysis, lang: str | None = None) -> dict[str, Any]:
    lang = lang or a.report_language
    return {
        "version": __version__, "sha256": a.sha256, "language": a.language, "lines": a.line_count, "today": a.today.isoformat(), "priority": a.priority,
        "tasks": [t.to_dict() for t in a.tasks],
        "log": {"entries": len(a.entries), "fatal": a.count("fatal"), "errors": a.count("error"), "warnings": a.count("warning"), "inferred_errors": sum(e.inferred for e in a.entries),
                "templates": [{"template": k, "count": n, "example": ex} for k, n, ex in a.templates],
                "bursts": [{"minute": b.minute.isoformat(), "count": b.count, "typical": b.typical} for b in a.bursts]},
        "keywords": [{"phrase": p, "score": float(s)} for p, s in a.keywords],
        "summary": [{"line": s.line, "text": s.text} for s in a.summary],
        "advice": [x.to_dict(lang) for x in a.advice],
    }


def as_json(a: Analysis, lang: str | None = None) -> str:
    return json.dumps(to_dict(a, lang), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def as_text(a: Analysis, lang: str | None = None, name: str | None = None) -> str:
    lang = lang or a.report_language
    m = MESSAGES[lang]
    open_tasks = [t for t in a.tasks if not t.done]
    out = [f"{m['title']}" + (f": {name}" if name else "")]
    out.append(f"  {m['language']}: {a.language}   {m['priority']}: {m['p_high'] if a.priority == 'high' else m['p_normal']}")
    out.append(f"  {m['tasks']}: {len(a.tasks)} ({len(open_tasks)} {m['open']}, {len(a.tasks) - len(open_tasks)} {m['done']}, "
               f"{len(adv.overdue(list(a.tasks), a.today))} {m['overdue']}, {sum(t.high and not t.done for t in a.tasks)} {m['high']})")
    if a.entries:
        out.append(f"  {m['logs']}: {len(a.entries)} {m['entries']}, {a.count('fatal') + a.count('error')} {m['errors']}, {a.count('warning')} {m['warnings']}")
        for _k, n, ex in a.templates[:3]:
            out.append(f"    {n}x {ex}")
    if a.keywords:
        out.append(f"  {m['keywords']}: " + ", ".join(p for p, _ in a.keywords))
    if a.summary:
        out.append(f"  {m['summary']}:")
        out += [f"    ({m['line']} {s.line}) {s.text}" for s in a.summary]
    out.append(f"  {m['next']}:")
    for x in a.advice:
        ref = f" [{m['line'] if len(x.lines) == 1 else m['lines']} {', '.join(map(str, x.lines))}]" if x.lines else ""
        out.append(f"    - {x.text(lang)}{ref}")
    return "\n".join(out) + "\n"


def as_markdown(a: Analysis, lang: str | None = None, name: str | None = None) -> str:
    lang = lang or a.report_language
    m = MESSAGES[lang]
    out = [f"# {m['title']}" + (f": {name}" if name else ""), "", f"**{m['priority']}:** {m['p_high'] if a.priority == 'high' else m['p_normal']}", ""]
    if a.tasks:
        out += [f"## {m['tasks']}", ""]
        for t in a.tasks:
            meta = ", ".join(x for x in (f"@{t.owner}" if t.owner else "", t.due.isoformat() if t.due else "", m["p_high"] if t.high else "") if x)
            out.append(f"- [{'x' if t.done else ' '}] {t.text} ({m['line']} {t.line}{', ' + meta if meta else ''})")
        out.append("")
    if a.keywords:
        out += [f"## {m['keywords']}", "", ", ".join(p for p, _ in a.keywords), ""]
    if a.summary:
        out += [f"## {m['summary']}", ""] + [f"> {s.text} ({m['line']} {s.line})" for s in a.summary] + [""]
    out += [f"## {m['next']}", ""] + [f"- {x.text(lang)}" + (f" ({m['line'] if len(x.lines) == 1 else m['lines']} {', '.join(map(str, x.lines))})" if x.lines else "") for x in a.advice]
    return "\n".join(out) + "\n"
