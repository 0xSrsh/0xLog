"""Tests for the presentation-independent tracking core."""

import json
import os
import tempfile
import unittest

from oxlog.core import TimeTracker
from oxlog.exceptions import (
    AliasNotFoundError,
    AmbiguousTaskError,
    EndTimeBeforeStartError,
    TaskAlreadyRunningError,
    TaskNotRunningError,
)


class TimeTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_file = os.path.join(self.temporary_directory.name, "records.json")
        self.tracker = TimeTracker(self.data_file)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_start_and_stop_return_records_and_persist_them(self) -> None:
        started = self.tracker.start_task("Write documentation", started_at=100.0)
        completed = self.tracker.stop_task("documentation", ended_at=160.0)

        self.assertEqual("Write documentation", started["task"])
        self.assertIsInstance(started["task_id"], str)
        self.assertEqual(100.0, started["start"])
        self.assertEqual("Write documentation", completed["task"])
        self.assertEqual(started["task_id"], completed["task_id"])
        self.assertEqual(60.0, completed["duration"])
        self.assertEqual(["Write documentation"], TimeTracker(self.data_file).get_recent_tasks())

    def test_invalid_task_transitions_raise_domain_exceptions(self) -> None:
        self.tracker.start_task("Write documentation", started_at=100.0)

        with self.assertRaises(TaskAlreadyRunningError):
            self.tracker.start_task("Write documentation", started_at=110.0)
        with self.assertRaises(TaskNotRunningError):
            self.tracker.stop_task("Missing task")

    def test_ambiguous_partial_task_name_exposes_matches(self) -> None:
        self.tracker.start_task("Write documentation", started_at=100.0)
        self.tracker.start_task("Write tests", started_at=100.0)

        with self.assertRaises(AmbiguousTaskError) as caught_error:
            self.tracker.stop_task("write", ended_at=160.0)

        self.assertEqual({"Write documentation", "Write tests"}, set(caught_error.exception.matches))

    def test_retrospective_record_rejects_reverse_chronology(self) -> None:
        with self.assertRaises(EndTimeBeforeStartError):
            self.tracker.add_record("Backfill", "14:00", end_value="13:00")

    def test_existing_task_and_its_alias_reuse_the_same_uuid(self) -> None:
        first_record = self.tracker.add_record("Review pull requests", "09:00", duration_value="20m")
        alias = self.tracker.add_alias("review", "Review pull requests")
        second_record = self.tracker.add_record("review", "10:00", duration_value="20m")

        self.assertEqual(first_record["task_id"], alias["task_id"])
        self.assertEqual(first_record["task_id"], second_record["task_id"])

    def test_alias_can_be_listed_reassigned_and_deleted(self) -> None:
        first_alias = self.tracker.add_alias("review", "Review pull requests")
        self.assertEqual([first_alias], self.tracker.get_aliases())

        reassigned_alias = self.tracker.add_alias("review", "Write documentation")
        self.assertEqual("Write documentation", reassigned_alias["task"])
        self.assertNotEqual(first_alias["task_id"], reassigned_alias["task_id"])
        self.assertEqual(reassigned_alias, self.tracker.remove_alias("review"))
        self.assertEqual([], self.tracker.get_aliases())
        with self.assertRaises(AliasNotFoundError):
            self.tracker.remove_alias("review")

    def test_legacy_data_is_migrated_to_uuid_task_identities(self) -> None:
        legacy_data = {
            "aliases": {"review": "Review pull requests"},
            "ongoing": {},
            "history": [{
                "task": "Review pull requests", "start": 100.0, "end": 160.0,
                "duration": 60.0, "date": "1970-01-01",
            }],
        }
        with open(self.data_file, "w", encoding="utf-8") as data_stream:
            json.dump(legacy_data, data_stream)

        migrated_tracker = TimeTracker(self.data_file)
        record = migrated_tracker.add_record("review", "10:00", duration_value="20m")
        with open(self.data_file, "r", encoding="utf-8") as data_stream:
            migrated_data = json.load(data_stream)

        self.assertEqual(1, len(migrated_data["tasks"]))
        self.assertEqual(record["task_id"], migrated_data["history"][0]["task_id"])


if __name__ == "__main__":
    unittest.main()
