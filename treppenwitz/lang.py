"""Language data: stopwords, month and weekday names, language detection and the wording of the reports (German and English)."""
from __future__ import annotations

import re
import unicodedata

STOP_DE = frozenset(["aber", "alle", "allem", "allen", "aller", "alles", "als", "also", "am", "an", "andere", "anderen", "auch", "auf", "aus", "bei", "beim", "bin", "bis", "bist", "da", "dabei", "dadurch", "dafuer", "dagegen", "dann", "das", "dass", "dem", "den", "der", "des", "die", "dies", "diese", "diesem", "diesen", "dieser", "dieses", "doch", "dort", "durch", "ein", "eine", "einem", "einen", "einer", "eines", "einmal", "er", "es", "etwas", "euch", "euer", "fuer", "gegen", "gewesen", "hab", "habe", "haben", "hat", "hatte", "hatten", "hier", "hin", "hinter", "ich", "ihm", "ihn", "ihnen", "ihr", "ihre", "ihrem", "ihren", "ihrer", "im", "in", "indem", "ins", "ist", "ja", "jede", "jedem", "jeden", "jeder", "jedes", "jetzt", "kann", "kein", "keine", "keinem", "keinen", "keiner", "koennen", "koennte", "machen", "man", "manche", "mehr", "mein", "meine", "meinem", "meinen", "meiner", "mit", "muss", "musste", "nach", "nicht", "noch", "nun", "nur", "ob", "oder", "ohne", "sehr", "sein", "seine", "seinem", "seinen", "seiner", "sich", "sie", "sind", "so", "solche", "soll", "sollen", "sollte", "sondern", "sonst", "ueber", "um", "und", "uns", "unser", "unter", "vom", "von", "vor", "waehrend", "war", "waren", "warum", "was", "weil", "weiter", "welche", "wenn", "wer", "werden", "wie", "wieder", "will", "wir", "wird", "wirst", "wo", "wollen", "wollte", "wurde", "wurden", "zu", "zum", "zur", "zwar", "zwischen"])

STOP_EN = frozenset(["a", "about", "above", "after", "again", "all", "also", "am", "an", "and", "any", "are", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself", "yourselves"])

MONTHS = {
    1: ("januar", "jan", "january"), 2: ("februar", "feb", "february"), 3: ("maerz", "mar", "march", "mrz"), 4: ("april", "apr"),
    5: ("mai", "may"), 6: ("juni", "jun", "june"), 7: ("juli", "jul", "july"), 8: ("august", "aug"),
    9: ("september", "sep", "sept"), 10: ("oktober", "okt", "october", "oct"), 11: ("november", "nov"), 12: ("dezember", "dez", "december", "dec"),
}
MONTH_LOOKUP = {name: n for n, names in MONTHS.items() for name in names}

WEEKDAYS = {
    0: ("montag", "monday"), 1: ("dienstag", "tuesday"), 2: ("mittwoch", "wednesday"), 3: ("donnerstag", "thursday"),
    4: ("freitag", "friday"), 5: ("samstag", "sonnabend", "saturday"), 6: ("sonntag", "sunday"),
}
WEEKDAY_LOOKUP = {name: n for n, names in WEEKDAYS.items() for name in names}


def fold(s: str) -> str:
    """Case-folded text with umlauts and sharp s written out (ä to ae, ß to ss), so matching ignores how a word was typed."""
    s = unicodedata.normalize("NFKC", s).casefold()
    return s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


_WORD = re.compile(r"[^\W\d_]+(?:['\-][^\W\d_]+)*")


def words(s: str) -> list[str]:
    """Words made of letters, with an inner hyphen or apostrophe kept (non-stop, e-mail). Numbers are not words."""
    return _WORD.findall(s)


def detect_language(text: str) -> str:
    """'de', 'en' or 'unknown', from how many of the words are stopwords of each language. Needs a clear margin."""
    toks = [fold(w) for w in words(text)]
    de = sum(t in STOP_DE for t in toks)
    en = sum(t in STOP_EN for t in toks)
    if max(de, en) < 3:
        return "unknown"
    if de >= 1.4 * en:
        return "de"
    if en >= 1.4 * de:
        return "en"
    return "unknown"


MESSAGES = {
    "en": {
        "title": "Analysis", "language": "Language", "tasks": "Tasks", "open": "open", "done": "done", "overdue": "overdue", "due_soon": "due within 3 days",
        "high": "high priority", "no_owner": "high priority without an owner", "logs": "Log", "entries": "entries", "errors": "errors", "warnings": "warnings",
        "templates": "Most frequent messages", "bursts": "Bursts", "keywords": "Key terms", "summary": "Summary", "next": "Next steps",
        "priority": "Priority", "p_high": "high", "p_normal": "normal", "none": "nothing found", "line": "line", "lines": "lines",
        "a_fatal": "{n} fatal or critical entr{y}: start with the first one",
        "a_errors": "{n} error entries in {k} distinct message(s); most frequent: {top} ({c}x)",
        "a_burst": "Errors cluster around {when}: {n} entries in one minute, against a typical {typical}",
        "a_overdue": "{n} open task(s) are past their due date: {names}",
        "a_soon": "{n} open task(s) fall due within 3 days: {names}",
        "a_owner": "{n} high priority task(s) have no owner: {names}",
        "a_undated": "{n} open tasks have no due date",
        "a_clear": "No errors, overdue tasks or unowned high priority tasks found",
    },
    "de": {
        "title": "Analyse", "language": "Sprache", "tasks": "Aufgaben", "open": "offen", "done": "erledigt", "overdue": "überfällig", "due_soon": "fällig in 3 Tagen",
        "high": "hohe Priorität", "no_owner": "hohe Priorität ohne Verantwortlichen", "logs": "Log", "entries": "Einträge", "errors": "Fehler", "warnings": "Warnungen",
        "templates": "Häufigste Meldungen", "bursts": "Häufungen", "keywords": "Schlüsselbegriffe", "summary": "Zusammenfassung", "next": "Nächste Schritte",
        "priority": "Priorität", "p_high": "hoch", "p_normal": "normal", "none": "nichts gefunden", "line": "Zeile", "lines": "Zeilen",
        "a_fatal": "{n} fatale oder kritische Einträge: mit dem ersten beginnen",
        "a_errors": "{n} Fehlereinträge in {k} verschiedenen Meldungen; häufigste: {top} ({c}x)",
        "a_burst": "Fehler häufen sich um {when}: {n} Einträge in einer Minute, üblich sind {typical}",
        "a_overdue": "{n} offene Aufgabe(n) sind überfällig: {names}",
        "a_soon": "{n} offene Aufgabe(n) sind in den nächsten 3 Tagen fällig: {names}",
        "a_owner": "{n} Aufgabe(n) mit hoher Priorität haben keinen Verantwortlichen: {names}",
        "a_undated": "{n} offene Aufgaben haben keinen Termin",
        "a_clear": "Keine Fehler, überfälligen Aufgaben oder Aufgaben hoher Priorität ohne Verantwortlichen gefunden",
    },
}
