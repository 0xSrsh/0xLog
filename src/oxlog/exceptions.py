"""Domain exceptions raised by :mod:`oxlog.core`."""

from typing import Iterable, Tuple


class TimeTrackerError(Exception):
    """Base exception for time-tracking errors."""


class DataFileError(TimeTrackerError):
    """Raised when the tracking data file cannot be read or written."""


class InvalidTimeFormatError(TimeTrackerError):
    """Raised when a supplied clock time cannot be parsed."""


class InvalidDurationFormatError(TimeTrackerError):
    """Raised when a supplied duration cannot be parsed."""


class MissingRecordTimingError(TimeTrackerError):
    """Raised when neither an end time nor a duration is supplied."""


class EndTimeBeforeStartError(TimeTrackerError):
    """Raised when a retrospective record ends before it starts."""


class TaskAlreadyRunningError(TimeTrackerError):
    """Raised when attempting to start a task that is already running."""


class TaskNotRunningError(TimeTrackerError):
    """Raised when a requested task is not currently running."""


class AliasNotFoundError(TimeTrackerError):
    """Raised when attempting to delete an alias that does not exist."""


class AmbiguousTaskError(TimeTrackerError):
    """Raised when a partial task name matches more than one running task."""

    def __init__(self, query: str, matches: Iterable[str]) -> None:
        self.query = query
        self.matches: Tuple[str, ...] = tuple(matches)
        super().__init__("Multiple tasks match {!r}.".format(query))
