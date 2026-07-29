"""Persistence and domain logic for 0xLog time-tracking records."""

import json
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .exceptions import (
    AliasNotFoundError,
    AmbiguousTaskError,
    DataFileError,
    EndTimeBeforeStartError,
    InvalidDurationFormatError,
    InvalidTimeFormatError,
    MissingRecordTimingError,
    TaskAlreadyRunningError,
    TaskNotRunningError,
)


DATA_FILE = os.path.join(os.path.expanduser("~"), ".0xlog.json")


class TimeTracker:
    """Store and retrieve UUID-backed time-tracking records in a JSON file.

    The class has no terminal or presentation concerns. Methods return records
    and query results on success, and raise domain exceptions on failure. This
    keeps the domain reusable by future non-terminal clients.
    """

    def __init__(self, data_file: str = DATA_FILE) -> None:
        self.data_file = data_file
        self._data: Dict[str, Any] = self._empty_data()
        self.load()

    @staticmethod
    def _empty_data() -> Dict[str, Any]:
        return {"tasks": {}, "aliases": {}, "ongoing": {}, "history": []}

    def load(self) -> None:
        """Load persisted records and migrate legacy data to preserve task identity."""
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as data_stream:
                data = json.load(data_stream)
        except (OSError, json.JSONDecodeError) as error:
            raise DataFileError("Could not read tracking data from {!r}.".format(self.data_file)) from error

        if not isinstance(data, dict):
            raise DataFileError("Tracking data must be a JSON object.")
        for key, expected_type in (("aliases", dict), ("ongoing", dict), ("history", list)):
            if key not in data or not isinstance(data[key], expected_type):
                raise DataFileError("Tracking data has an invalid {!r} section.".format(key))

        self._data = data
        if self._migrate_data():
            self._save()

    def _migrate_data(self) -> bool:
        """Upgrade pre-UUID files so historical and future records share identities."""
        changed = False
        if "tasks" not in self._data:
            self._data["tasks"] = {}
            changed = True
        if not isinstance(self._data["tasks"], dict):
            raise DataFileError("Tracking data has an invalid 'tasks' section.")

        for task_id, task in self._data["tasks"].items():
            if not isinstance(task_id, str) or not isinstance(task, dict) or not isinstance(task.get("name"), str):
                raise DataFileError("Tracking data has an invalid task definition.")

        for record in self._data["history"]:
            if not isinstance(record, dict) or not isinstance(record.get("task"), str):
                raise DataFileError("Tracking data has an invalid history record.")
            task_id, was_created = self._get_or_create_task(record["task"])
            if record.get("task_id") != task_id:
                record["task_id"] = task_id
                changed = True
            changed = changed or was_created

        for task_name, ongoing_value in list(self._data["ongoing"].items()):
            if not isinstance(task_name, str):
                raise DataFileError("Tracking data has an invalid ongoing task.")
            task_id, was_created = self._get_or_create_task(task_name)
            changed = changed or was_created
            if isinstance(ongoing_value, (int, float)):
                self._data["ongoing"][task_name] = {"task_id": task_id, "start": ongoing_value}
                changed = True
            elif (
                not isinstance(ongoing_value, dict)
                or not isinstance(ongoing_value.get("start"), (int, float))
                or ongoing_value.get("task_id") not in self._data["tasks"]
            ):
                raise DataFileError("Tracking data has an invalid ongoing task.")

        for alias, task_reference in list(self._data["aliases"].items()):
            if not isinstance(alias, str) or not isinstance(task_reference, str):
                raise DataFileError("Tracking data has an invalid alias.")
            if task_reference in self._data["tasks"]:
                continue
            task_id, was_created = self._get_or_create_task(task_reference)
            self._data["aliases"][alias] = task_id
            changed = True
            changed = changed or was_created
        return changed

    def _save(self) -> None:
        try:
            with open(self.data_file, "w", encoding="utf-8") as data_stream:
                json.dump(self._data, data_stream, indent=4)
        except OSError as error:
            raise DataFileError("Could not save tracking data to {!r}.".format(self.data_file)) from error

    @staticmethod
    def parse_time(time_value: str) -> float:
        """Parse a clock time for today and return its Unix timestamp."""
        normalized_value = time_value.strip().lower().replace(".", ":")
        formats = ("%H:%M", "%H", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p")
        for time_format in formats:
            try:
                parsed_time = datetime.strptime(normalized_value, time_format).time()
                return datetime.combine(datetime.now().date(), parsed_time).timestamp()
            except ValueError:
                continue
        raise InvalidTimeFormatError(
            "Invalid time format: {!r}. Try '10 am' or '14:30'.".format(time_value)
        )

    @staticmethod
    def parse_duration(duration_value: str) -> float:
        """Parse a duration string and return its value in seconds."""
        normalized_value = duration_value.strip().lower()
        if normalized_value.isdigit():
            return float(normalized_value) * 60
        matches = re.findall(
            r"([\d.]+)\s*(h|hr|hours?|m|min|minutes?|s|sec|seconds?)", normalized_value
        )
        if not matches:
            raise InvalidDurationFormatError(
                "Invalid duration format: {!r}. Try '20m' or '1.5h'.".format(duration_value)
            )

        total_seconds = 0.0
        for amount, unit in matches:
            if unit.startswith("h"):
                total_seconds += float(amount) * 3600
            elif unit.startswith("m"):
                total_seconds += float(amount) * 60
            else:
                total_seconds += float(amount)
        return total_seconds

    def resolve_task_name(self, name_or_alias: str) -> str:
        """Return a canonical name so aliases never create duplicate task identities."""
        task_id = self._data["aliases"].get(name_or_alias)
        if task_id is None:
            return name_or_alias
        return self._data["tasks"][task_id]["name"]

    def add_record(
        self, name_or_alias: str, start_value: str, end_value: Optional[str] = None,
        duration_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a completed record while preserving its stable task UUID."""
        task_name = self.resolve_task_name(name_or_alias)
        task_id, _ = self._get_or_create_task(task_name)
        start_time = self.parse_time(start_value)
        if end_value:
            end_time = self.parse_time(end_value)
            duration = end_time - start_time
            if duration < 0:
                raise EndTimeBeforeStartError("End time cannot be before start time.")
        elif duration_value:
            duration = self.parse_duration(duration_value)
            end_time = start_time + duration
        else:
            raise MissingRecordTimingError("Provide either an end time or a duration.")

        record = self._create_record(task_id, task_name, start_time, end_time, duration)
        self._data["history"].append(record)
        self._save()
        return dict(record)

    def start_task(self, name_or_alias: str, started_at: Optional[float] = None) -> Dict[str, Any]:
        """Start a UUID-backed task so stopping it cannot change its identity."""
        task_name = self.resolve_task_name(name_or_alias)
        if task_name in self._data["ongoing"]:
            raise TaskAlreadyRunningError("Task {!r} is already running.".format(task_name))

        task_id, _ = self._get_or_create_task(task_name)
        start_time = time.time() if started_at is None else started_at
        self._data["ongoing"][task_name] = {"task_id": task_id, "start": start_time}
        self._save()
        return {"task_id": task_id, "task": task_name, "start": start_time}

    def stop_task(self, name: str, ended_at: Optional[float] = None) -> Dict[str, Any]:
        """Stop a running task identified by exact or unique partial name."""
        task_name = self._find_running_task(name)
        ongoing_record = self._data["ongoing"].pop(task_name)
        start_time = ongoing_record["start"]
        end_time = time.time() if ended_at is None else ended_at
        record = self._create_record(
            ongoing_record["task_id"], task_name, start_time, end_time, end_time - start_time
        )
        self._data["history"].append(record)
        self._save()
        return dict(record)

    def stop_all(self, ended_at: Optional[float] = None) -> List[Dict[str, Any]]:
        """Stop every running task and return the completed records."""
        end_time = time.time() if ended_at is None else ended_at
        return [self.stop_task(task_name, ended_at=end_time) for task_name in list(self._data["ongoing"])]

    def add_alias(self, alias: str, task_name: str) -> Dict[str, str]:
        """Create or reassign an alias without creating a second task identity."""
        canonical_name = self.resolve_task_name(task_name)
        task_id, _ = self._get_or_create_task(canonical_name)
        self._data["aliases"][alias] = task_id
        self._save()
        return {"alias": alias, "task_id": task_id, "task": canonical_name}

    def remove_alias(self, alias: str) -> Dict[str, str]:
        """Delete an alias and return the mapping that was removed."""
        try:
            task_id = self._data["aliases"].pop(alias)
        except KeyError as error:
            raise AliasNotFoundError("Alias {!r} does not exist.".format(alias)) from error
        self._save()
        return {"alias": alias, "task_id": task_id, "task": self._data["tasks"][task_id]["name"]}

    def get_aliases(self) -> List[Dict[str, str]]:
        """Return aliases with IDs so callers can show their persistent targets."""
        return [
            {"alias": alias, "task_id": task_id, "task": self._data["tasks"][task_id]["name"]}
            for alias, task_id in sorted(self._data["aliases"].items())
        ]

    def get_ongoing(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        """Return running tasks with stable UUIDs and elapsed durations."""
        current_time = time.time() if now is None else now
        return [
            {"task_id": details["task_id"], "task": task, "start": details["start"],
             "elapsed": current_time - details["start"]}
            for task, details in self._data["ongoing"].items()
        ]

    def get_today_total(self, now: Optional[float] = None) -> float:
        """Return completed and active tracked seconds for today."""
        current_time = time.time() if now is None else now
        today = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d")
        completed_seconds = sum(
            record["duration"] for record in self._data["history"] if record["date"] == today
        )
        active_seconds = sum(current_time - details["start"] for details in self._data["ongoing"].values())
        return completed_seconds + active_seconds

    def get_recent_tasks(self, limit: int = 10) -> List[str]:
        """Return unique task names, ordered from most recently completed."""
        task_ids = set()
        recent_tasks = []
        for record in reversed(self._data["history"]):
            if record["task_id"] not in task_ids:
                task_ids.add(record["task_id"])
                recent_tasks.append(record["task"])
            if len(recent_tasks) == limit:
                break
        return recent_tasks

    def get_daily_report(self, date: Optional[str] = None) -> Mapping[str, float]:
        """Return completed durations grouped by task for the requested date."""
        report_date = date or datetime.now().strftime("%Y-%m-%d")
        task_totals: Dict[str, float] = {}
        for record in self._data["history"]:
            if record["date"] == report_date:
                task_totals[record["task"]] = task_totals.get(record["task"], 0.0) + record["duration"]
        return task_totals

    def _get_or_create_task(self, task_name: str) -> Tuple[str, bool]:
        """Find a task by name before generating an ID to avoid duplicate history."""
        for task_id, task in self._data["tasks"].items():
            if task["name"] == task_name:
                return task_id, False
        task_id = str(uuid.uuid4())
        self._data["tasks"][task_id] = {"name": task_name}
        return task_id, True

    def _find_running_task(self, name: str) -> str:
        canonical_name = self.resolve_task_name(name)
        if canonical_name in self._data["ongoing"]:
            return canonical_name
        matches = [task for task in self._data["ongoing"] if name.lower() in task.lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise AmbiguousTaskError(name, matches)
        raise TaskNotRunningError("Task matching {!r} is not currently running.".format(name))

    @staticmethod
    def _create_record(task_id: str, task: str, start: float, end: float, duration: float) -> Dict[str, Any]:
        return {
            "task_id": task_id,
            "task": task,
            "start": start,
            "end": end,
            "duration": duration,
            "date": datetime.fromtimestamp(start).strftime("%Y-%m-%d"),
        }
