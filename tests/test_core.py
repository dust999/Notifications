"""Run from the project folder: python -m unittest discover -s tests"""
import datetime
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reminder_check import ReminderChecker
from utils import load_json, prepare_data_files, save_json


def at(year, month, day, hour=12, minute=0):
    return datetime.datetime(year, month, day, hour, minute)


class MonthlyTest(unittest.TestCase):
    def monthly(self, day, now, last=None):
        return ReminderChecker.monthly({"monthly_day": day, "time": "10:00"}, now, last)

    def test_day_30_fires_on_last_day_of_february(self):
        self.assertTrue(self.monthly(30, at(2026, 2, 28)))
        self.assertFalse(self.monthly(30, at(2026, 2, 27)))

    def test_day_31_fires_on_30th_in_30_day_month(self):
        self.assertTrue(self.monthly(31, at(2026, 11, 30)))

    def test_normal_day(self):
        self.assertFalse(self.monthly(15, at(2026, 3, 14)))
        self.assertFalse(self.monthly(15, at(2026, 3, 15, 9, 59)))
        self.assertTrue(self.monthly(15, at(2026, 3, 15, 10, 0)))

    def test_only_once_per_month(self):
        done = at(2026, 3, 15, 10, 0).isoformat()
        self.assertFalse(self.monthly(15, at(2026, 3, 20), done))
        self.assertTrue(self.monthly(15, at(2026, 4, 15, 10, 0), done))


class DailyWeeklyTest(unittest.TestCase):
    def test_daily_once_per_day(self):
        r = {"time": "09:00"}
        self.assertFalse(ReminderChecker.daily(r, at(2026, 5, 4, 8, 59), None))
        self.assertTrue(ReminderChecker.daily(r, at(2026, 5, 4, 9, 0), None))
        done = at(2026, 5, 4, 9, 0).isoformat()
        self.assertFalse(ReminderChecker.daily(r, at(2026, 5, 4, 20, 0), done))
        self.assertTrue(ReminderChecker.daily(r, at(2026, 5, 5, 9, 0), done))

    def test_weekly_only_on_chosen_days(self):
        r = {"time": "09:00", "weekly_days": [0, 2]}  # Mon, Wed
        self.assertTrue(ReminderChecker.weekly(r, at(2026, 5, 4, 9, 0), None))   # Monday
        self.assertFalse(ReminderChecker.weekly(r, at(2026, 5, 5, 9, 0), None))  # Tuesday


class YearlyTest(unittest.TestCase):
    def test_feb_29_falls_back_to_28_in_common_year(self):
        r = {"time": "09:00", "yearly_month": 2, "yearly_day": 29}
        self.assertTrue(ReminderChecker.yearly(r, at(2026, 2, 28, 9, 0), None))


class JsonStorageTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "notify.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_returns_default(self):
        self.assertEqual(load_json(self.path, []), [])
        self.assertEqual(load_json(self.path, {}), {})

    def test_save_keeps_previous_version_and_leaves_no_temp_file(self):
        save_json(self.path, [{"id": "1"}])
        save_json(self.path, [{"id": "2"}])
        self.assertEqual(load_json(self.path), [{"id": "2"}])
        with open(self.path + ".bak", encoding="utf-8") as f:
            self.assertEqual(json.load(f), [{"id": "1"}])
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_damaged_file_is_restored_from_backup_and_kept_aside(self):
        save_json(self.path, [{"id": "1"}])
        save_json(self.path, [{"id": "2"}])
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('[{"id": "2"')  # cut off mid-write
        self.assertEqual(load_json(self.path), [{"id": "1"}])
        kept = [n for n in os.listdir(self.dir.name) if ".corrupt-" in n]
        self.assertEqual(len(kept), 1)

    def test_damaged_file_without_backup_is_still_kept_aside(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{oops")
        self.assertEqual(load_json(self.path, []), [])
        self.assertTrue(any(".corrupt-" in n for n in os.listdir(self.dir.name)))


class PrepareDataFilesTest(unittest.TestCase):
    PATHS = ["user_data/notify.json", "user_data/completed.json"]

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.app = self.dir.name
        os.makedirs(os.path.join(self.app, "sample_data"))
        for name in ("notify.json", "completed.json"):
            self.write(os.path.join("sample_data", name), f"sample {name}")

    def tearDown(self):
        self.dir.cleanup()

    def write(self, rel, text):
        with open(os.path.join(self.app, rel), "w", encoding="utf-8") as f:
            f.write(text)

    def read(self, rel):
        with open(os.path.join(self.app, rel), encoding="utf-8") as f:
            return f.read()

    def test_fresh_copy_gets_demo_data(self):
        created = prepare_data_files(self.PATHS, self.app)
        self.assertEqual(created, self.PATHS)
        self.assertEqual(self.read("user_data/notify.json"), "sample notify.json")

    def test_old_files_from_app_folder_are_moved_with_backup(self):
        self.write("notify.json", "my reminders")
        self.write("notify.json.bak", "my previous reminders")
        created = prepare_data_files(self.PATHS, self.app)
        self.assertEqual(self.read("user_data/notify.json"), "my reminders")
        self.assertEqual(self.read("user_data/notify.json.bak"), "my previous reminders")
        self.assertFalse(os.path.exists(os.path.join(self.app, "notify.json")))
        self.assertEqual(created, ["user_data/completed.json"])  # only the missing one came from samples

    def test_existing_files_are_never_touched(self):
        os.makedirs(os.path.join(self.app, "user_data"))
        self.write("user_data/notify.json", "current")
        self.write("notify.json", "stale copy in the app folder")
        prepare_data_files(self.PATHS, self.app)
        self.assertEqual(self.read("user_data/notify.json"), "current")
        self.assertEqual(self.read("notify.json"), "stale copy in the app folder")


class SampleDataTest(unittest.TestCase):
    """A fresh clone starts from sample_data/, so it has to stay valid."""

    def load(self, name):
        with open(os.path.join(ROOT, "sample_data", name), encoding="utf-8") as f:
            return json.load(f)

    def test_all_sample_files_are_valid_json(self):
        for name in ("notify.json", "backlog.json", "completed.json", "config_dynamic.json"):
            self.load(name)

    def test_config_has_keys_the_app_needs_at_startup(self):
        config = self.load("config_dynamic.json")
        self.assertIn("reminder_check_interval_sec", config["settings_dialog"])
        self.assertIn("add_notify_dialog", config)

    def test_sample_reminders_are_well_formed(self):
        for r in self.load("notify.json"):
            self.assertTrue(r["id"] and r["text"] and r["time"])
            self.assertIn(r["recurrence_type"], ("once", "daily", "weekly", "monthly", "yearly"))
            if r.get("icon"):
                self.assertTrue(os.path.exists(os.path.join(ROOT, r["icon"])), r["icon"])


if __name__ == "__main__":
    unittest.main()
