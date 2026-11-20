"""treppenwitz: tasks, log entries, key terms, a summary and next steps from notes and logs. Standard library only."""
from ._version import __version__
from .analyze import Analysis, analyse
from .errors import TextError
from .logs import Burst, LogEntry
from .tasks import Task

__all__ = ["Analysis", "Burst", "LogEntry", "Task", "TextError", "__version__", "analyse"]
