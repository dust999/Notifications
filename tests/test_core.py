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
import schedule
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


class ScheduleTest(unittest.TestCase):
    """Next occurrence and plain-words labels used by the list window."""
    NOW = datetime.datetime(2026, 11, 9, 13, 20)  # Monday

    def test_daily_due_later_today_then_tomorrow_once_shown(self):
        r = {"recurrence_type": "daily", "time": "20:00"}
        self.assertEqual(schedule.next_occurrence(r, self.NOW), datetime.datetime(2026, 11, 9, 20, 0))
        shown = datetime.datetime(2026, 11, 9, 20, 0, 5)
        self.assertEqual(schedule.next_occurrence(r, self.NOW, shown.isoformat()), datetime.datetime(2026, 11, 10, 20, 0))

    def test_weekly_skips_other_days(self):
        r = {"recurrence_type": "weekly", "time": "10:30", "weekly_days": [2, 4]}
        self.assertEqual(schedule.next_occurrence(r, self.NOW), datetime.datetime(2026, 11, 11, 10, 30))

    def test_monthly_clamps_and_moves_on_after_shown(self):
        r = {"recurrence_type": "monthly", "time": "10:00", "monthly_day": 31}
        self.assertEqual(schedule.next_occurrence(r, self.NOW), datetime.datetime(2026, 11, 30, 10, 0))
        r = {"recurrence_type": "monthly", "time": "09:00", "monthly_day": 5}
        shown = datetime.datetime(2026, 11, 5, 9, 0, 3)
        self.assertEqual(schedule.next_occurrence(r, self.NOW, shown), datetime.datetime(2026, 12, 5, 9, 0))

    def test_yearly_next_year_when_shown(self):
        r = {"recurrence_type": "yearly", "time": "09:00", "yearly_month": 6, "yearly_day": 16}
        shown = datetime.datetime(2026, 6, 16, 9, 0)
        self.assertEqual(schedule.next_occurrence(r, self.NOW, shown), datetime.datetime(2027, 6, 16, 9, 0))

    def test_missed_occurrence_rolls_to_next_like_the_checker(self):
        # Mar 1 passed while the app was off; the checker only shows yearly ones in their month
        r = {"recurrence_type": "yearly", "time": "09:00", "yearly_month": 3, "yearly_day": 1}
        self.assertEqual(schedule.next_occurrence(r, self.NOW), datetime.datetime(2027, 3, 1, 9, 0))
        self.assertFalse(ReminderChecker.yearly(r, self.NOW, None))
        # Earlier today and not shown yet: still due now, the checker will show it
        r = {"recurrence_type": "daily", "time": "09:00"}
        self.assertEqual(schedule.next_occurrence(r, self.NOW), datetime.datetime(2026, 11, 9, 9, 0))
        self.assertTrue(ReminderChecker.daily(r, self.NOW, None))

    def test_describe_rule(self):
        self.assertEqual(schedule.describe_rule({"recurrence_type": "weekly", "time": "13:00", "weekly_days": [0, 1, 2, 3, 4]}), "Weekdays at 13:00")
        self.assertEqual(schedule.describe_rule({"recurrence_type": "monthly", "time": "09:00", "monthly_day": 2}), "Every month on the 2nd at 09:00")
        self.assertEqual(schedule.describe_rule({"recurrence_type": "monthly", "time": "09:00", "monthly_day": 11}), "Every month on the 11th at 09:00")
        self.assertEqual(schedule.describe_rule({"recurrence_type": "yearly", "time": "09:00", "yearly_month": 3, "yearly_day": 1}), "Every year on Mar 1 at 09:00")

    def test_groups_and_labels(self):
        at = lambda d, h=9: datetime.datetime(2026, 11, d, h, 0)
        self.assertEqual(schedule.group_of(at(9, 20), self.NOW), "Today")
        self.assertEqual(schedule.group_of(at(10), self.NOW), "Tomorrow")
        self.assertEqual(schedule.group_of(at(15), self.NOW), "This week")  # Sunday
        self.assertEqual(schedule.group_of(at(16), self.NOW), "Later")
        self.assertEqual(schedule.relative_label(at(9, 16), self.NOW), "in 2 h")
        self.assertEqual(schedule.relative_label(at(10), self.NOW), "Tue 09:00")
        self.assertEqual(schedule.relative_label(datetime.datetime(2027, 3, 1, 9), self.NOW), "Mar 1, 2027")
        self.assertEqual(schedule.countdown(datetime.datetime(2026, 11, 9, 19, 38), self.NOW), "in 6 h 18 min")

    def test_category_from_old_icon_path(self):
        self.assertEqual(schedule.category_of({"icon": "icons/home.png"}), "personal")
        self.assertEqual(schedule.category_of({"icon": ""}), "none")
        self.assertEqual(schedule.category_of({"category": "health", "icon": "icons/work.png"}), "health")


if __name__ == "__main__":
    unittest.main()


class CalendarOccurrencesTest(unittest.TestCase):
    def test_daily_and_weekly_fill_a_range(self):
        first, last = datetime.date(2026, 11, 1), datetime.date(2026, 11, 30)
        daily = {"recurrence_type": "daily", "time": "11:00"}
        self.assertEqual(len(schedule.occurrences_between(daily, first, last)), 30)
        weekly = {"recurrence_type": "weekly", "time": "18:00", "weekly_days": [5]}
        days = [o.day for o in schedule.occurrences_between(weekly, first, last)]
        self.assertEqual(days, [7, 14, 21, 28])

    def test_monthly_yearly_once(self):
        first, last = datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)
        monthly = {"recurrence_type": "monthly", "time": "09:00", "monthly_day": 31}
        occ = schedule.occurrences_between(monthly, first, last)
        self.assertEqual(len(occ), 12)
        self.assertEqual(occ[1].date(), datetime.date(2026, 2, 28))  # shorter month: last day
        yearly = {"recurrence_type": "yearly", "time": "09:00", "yearly_month": 6, "yearly_day": 16}
        self.assertEqual([o.date() for o in schedule.occurrences_between(yearly, first, last)],
                         [datetime.date(2026, 6, 16)])
        once = {"recurrence_type": "once", "time": "15:30", "date": "2026-11-14"}
        self.assertEqual(len(schedule.occurrences_between(once, first, last)), 1)
        self.assertEqual(schedule.occurrences_between(once, datetime.date(2026, 11, 15), last), [])

    def test_range_starting_mid_month(self):
        monthly = {"recurrence_type": "monthly", "time": "09:00", "monthly_day": 10}
        occ = schedule.occurrences_between(monthly, datetime.date(2026, 11, 20), datetime.date(2027, 1, 5))
        self.assertEqual([o.date() for o in occ], [datetime.date(2026, 12, 10)])


class HeadsUpTest(unittest.TestCase):
    def test_birthday_a_month_earlier(self):
        r = {"id": "b", "recurrence_type": "yearly", "time": "09:00", "yearly_month": 6, "yearly_day": 16,
             "remind_before_days": 30}
        self.assertIsNone(schedule.early_occurrence(r, at(2026, 5, 17, 8, 59)))
        self.assertEqual(schedule.early_occurrence(r, at(2026, 5, 17, 9, 0)), at(2026, 6, 16, 9, 0))
        # Shown once: not again the next day, but again a year later
        self.assertIsNone(schedule.early_occurrence(r, at(2026, 5, 18, 9, 0), at(2026, 5, 17, 9, 0)))
        self.assertEqual(schedule.early_occurrence(r, at(2027, 5, 17, 9, 0), "2026-05-17T09:00:00"),
                         at(2027, 6, 16, 9, 0))

    def test_birthday_early_in_january_from_december(self):
        r = {"id": "b", "recurrence_type": "yearly", "time": "10:00", "yearly_month": 1, "yearly_day": 5,
             "remind_before_days": 30}
        self.assertEqual(schedule.early_occurrence(r, at(2026, 12, 6, 10, 0)), at(2027, 1, 5, 10, 0))

    def test_bills_two_weeks_earlier(self):
        r = {"id": "m", "recurrence_type": "monthly", "time": "09:00", "monthly_day": 10, "remind_before_days": 14}
        self.assertIsNone(schedule.early_occurrence(r, at(2026, 11, 20, 9, 0)))
        self.assertEqual(schedule.early_occurrence(r, at(2026, 11, 26, 9, 0)), at(2026, 12, 10, 9, 0))

    def test_once_two_weeks_earlier(self):
        r = {"id": "o", "recurrence_type": "once", "time": "15:30", "date": "2026-12-01", "remind_before_days": 14}
        self.assertIsNone(schedule.early_occurrence(r, at(2026, 11, 17, 15, 29)))
        self.assertEqual(schedule.early_occurrence(r, at(2026, 11, 17, 15, 30)), at(2026, 12, 1, 15, 30))

    def test_daily_never_gets_heads_up(self):
        r = {"id": "d", "recurrence_type": "daily", "time": "11:00", "remind_before_days": 30}
        self.assertIsNone(schedule.early_occurrence(r, at(2026, 11, 9, 12, 0)))

    def test_choices_per_repeat(self):
        now = at(2026, 11, 9, 12, 0)
        self.assertEqual(schedule.lead_choices({"recurrence_type": "daily", "time": "11:00"}, now), [])
        self.assertEqual(schedule.lead_choices({"recurrence_type": "weekly", "time": "11:00"}, now), [])
        self.assertEqual(schedule.lead_choices({"recurrence_type": "monthly", "time": "09:00", "monthly_day": 10}, now),
                         [1, 3, 7, 14])
        self.assertEqual(schedule.lead_choices({"recurrence_type": "yearly", "time": "09:00", "yearly_month": 6,
                                                "yearly_day": 16}, now), [1, 3, 7, 14, 30])
        soon = {"recurrence_type": "once", "time": "15:30", "date": "2026-11-14"}  # 5 days away
        self.assertEqual(schedule.lead_choices(soon, now), [1, 3])
        far = {"recurrence_type": "once", "time": "15:30", "date": "2027-01-20"}
        self.assertEqual(schedule.lead_choices(far, now), [1, 3, 7, 14, 30])
        self.assertEqual(schedule.lead_choices({"recurrence_type": "once", "time": "09:00", "date": "2026-11-10"}, now), [])

    def test_labels(self):
        self.assertEqual([schedule.lead_label(d) for d in schedule.LEAD_DAYS],
                         ["1 day", "3 days", "1 week", "2 weeks", "1 month"])


class SeveralHeadsUpsTest(unittest.TestCase):
    R = {"id": "b", "recurrence_type": "yearly", "time": "09:00", "yearly_month": 6, "yearly_day": 16,
         "remind_before_days": [30, 14, 3]}

    def test_each_fires_once_and_the_day_itself_too(self):
        shown = {}
        def due_at(when):
            due = schedule.due_heads_ups(self.R, when, shown)
            for days, _occ in due:
                shown[f"b:early:{days}"] = when.isoformat()
            return [d for d, _ in due]
        self.assertEqual(due_at(at(2026, 5, 17, 9, 0)), [30])
        self.assertEqual(due_at(at(2026, 5, 18, 9, 0)), [])
        self.assertEqual(due_at(at(2026, 6, 2, 9, 0)), [14])
        self.assertEqual(due_at(at(2026, 6, 13, 9, 0)), [3])
        self.assertEqual(due_at(at(2026, 6, 15, 9, 0)), [])
        # On the day the reminder itself fires, as always
        self.assertTrue(ReminderChecker.yearly(self.R, at(2026, 6, 16, 9, 0), None))

    def test_missed_ones_come_together(self):
        due = schedule.due_heads_ups(self.R, at(2026, 6, 14, 9, 0), {})
        self.assertEqual(sorted(d for d, _ in due), [3, 14])
        self.assertEqual(min(due)[0], 3)  # the app shows the closest one

    def test_old_single_number_and_old_mark(self):
        old = {"id": "o", "recurrence_type": "once", "time": "15:30", "date": "2026-12-01", "remind_before_days": 7}
        self.assertEqual(schedule.leads_of(old), [7])
        self.assertEqual(schedule.due_heads_ups(old, at(2026, 11, 24, 15, 30), {}), [(7, at(2026, 12, 1, 15, 30))])
        # Already shown by an older version (single <id>:early mark): not again
        self.assertEqual(schedule.due_heads_ups(old, at(2026, 11, 25, 15, 30), {"o:early": "2026-11-24T15:30:00"}), [])

    def test_leads_parsing_and_text(self):
        self.assertEqual(schedule.leads_of({"remind_before_days": [3, 30, 3, 0, "x"]}), [30, 3])
        self.assertEqual(schedule.leads_of({}), [])
        self.assertEqual(schedule.leads_text([3, 30, 14]), "1 month, 2 weeks and 3 days")
        self.assertEqual(schedule.leads_text([1]), "1 day")


class WeekStartTest(unittest.TestCase):
    def tearDown(self):
        schedule.set_week_start(0)

    def test_monday_first_by_default(self):
        self.assertEqual(schedule.week_order(), [0, 1, 2, 3, 4, 5, 6])
        self.assertEqual(schedule.week_start_of(datetime.date(2026, 11, 1)), datetime.date(2026, 10, 26))

    def test_sunday_first(self):
        schedule.set_week_start(6)
        self.assertEqual(schedule.week_order(), [6, 0, 1, 2, 3, 4, 5])
        nov1 = datetime.date(2026, 11, 1)  # a Sunday
        self.assertEqual(schedule.column_of(nov1), 0)
        self.assertEqual(schedule.week_start_of(nov1), nov1)
        self.assertEqual(schedule.column_of(datetime.date(2026, 11, 7)), 6)  # Saturday ends the row
        self.assertEqual(schedule.week_start_of(datetime.date(2026, 12, 1)), datetime.date(2026, 11, 29))

    def test_bad_value_falls_back_to_monday(self):
        schedule.set_week_start(9)
        self.assertEqual(schedule.week_start(), 0)
