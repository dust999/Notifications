"""When a reminder fires next, and how to describe it in plain words.

Pure functions (no Qt), shared by the list window, the editor preview and the tests.
A reminder occurrence counts as handled when the reminder's last "completed_at"
is at or after that occurrence (the same rule ReminderChecker applies per period).
"""
import calendar
import datetime

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CATEGORIES = ["work", "personal", "health", "shopping", "none"]
CATEGORY_NAMES = {"work": "Work", "personal": "Personal", "health": "Health",
                  "shopping": "Shopping", "none": "None"}
# Reminders saved by older versions only have an icon path
_ICON_TO_CATEGORY = {"work": "work", "home": "personal", "health": "health", "shopping": "shopping"}


def category_of(reminder):
    cat = reminder.get("category")
    if cat in CATEGORIES:
        return cat
    icon = (reminder.get("icon") or "").replace("\\", "/").rsplit("/", 1)[-1].split(".")[0]
    return _ICON_TO_CATEGORY.get(icon, "none")


def _time_of(reminder):
    try:
        hour, minute = map(int, (reminder.get("time") or "").split(":"))
        return datetime.time(hour, minute)
    except ValueError:
        return None


def _clamp_day(year, month, day):
    return min(day, calendar.monthrange(year, month)[1])


def _occurrences(reminder, start):
    """Occurrences of the reminder from `start` (a date) onwards, in order (about 2 years ahead)."""
    t = _time_of(reminder)
    if t is None:
        return
    kind = reminder.get("recurrence_type")
    if kind == "once":
        try:
            yield datetime.datetime.combine(datetime.date.fromisoformat(reminder.get("date", "")), t)
        except ValueError:
            pass
        return
    if kind in ("daily", "weekly"):
        days = set(reminder.get("weekly_days") or range(7)) if kind == "weekly" else set(range(7))
        for i in range(800):
            d = start + datetime.timedelta(days=i)
            if d.weekday() in days:
                yield datetime.datetime.combine(d, t)
        return
    if kind == "monthly":
        day = reminder.get("monthly_day", 1)
        y, m = start.year, start.month
        for _ in range(26):
            yield datetime.datetime(y, m, _clamp_day(y, m, day), t.hour, t.minute)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return
    if kind == "yearly":
        month, day = reminder.get("yearly_month", 1), reminder.get("yearly_day", 1)
        for y in range(start.year, start.year + 3):
            yield datetime.datetime(y, month, _clamp_day(y, month, day), t.hour, t.minute)


def occurrences_between(reminder, first, last):
    """Occurrences on the days first..last (dates, both included), in order. For the calendar."""
    found = []
    for occ in _occurrences(reminder, first):
        if occ.date() > last:
            break
        if occ.date() >= first:
            found.append(occ)
    return found


def is_date_specific(reminder):
    """One-time, monthly and yearly reminders belong to particular dates (bills, birthdays);
    daily and weekly ones repeat all the time."""
    return reminder.get("recurrence_type") in ("once", "monthly", "yearly")


def _period_start(reminder, now):
    kind = reminder.get("recurrence_type")
    if kind == "monthly":
        return now.date().replace(day=1)
    if kind == "yearly":
        return now.date().replace(month=1, day=1)
    return now.date()


def next_occurrence(reminder, now, completed_at=None):
    """The next occurrence not handled yet. It can be in the past (due right now).
    `completed_at` is an ISO string or datetime of the last time it was shown."""
    if isinstance(completed_at, str):
        try:
            completed_at = datetime.datetime.fromisoformat(completed_at)
        except ValueError:
            completed_at = None
    for occ in _occurrences(reminder, _period_start(reminder, now)):
        if completed_at is not None and completed_at >= occ:
            continue
        if occ < now and not _still_due(reminder, occ, now):
            continue  # missed while the app was off; the checker won't show it any more
        return occ
    return None


def _still_due(reminder, occ, now):
    """Mirror ReminderChecker: which past, unshown occurrences it would still show now."""
    kind = reminder.get("recurrence_type")
    if kind == "once":
        return True
    if kind in ("daily", "weekly"):
        return occ.date() == now.date()
    if kind == "monthly":
        return (occ.year, occ.month) == (now.year, now.month)
    if kind == "yearly":
        return (occ.year, occ.month) == (now.year, now.month)
    return False


def _ordinal(n):
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def describe_rule(reminder):
    """'Weekdays at 13:00', 'Every month on the 10th at 09:00', ..."""
    at = f"at {reminder.get('time', '')}"
    kind = reminder.get("recurrence_type")
    if kind == "daily":
        return f"Daily {at}"
    if kind == "weekly":
        days = sorted(set(reminder.get("weekly_days") or range(7)))
        if days == list(range(7)):
            return f"Daily {at}"
        if days == [0, 1, 2, 3, 4]:
            return f"Weekdays {at}"
        if days == [5, 6]:
            return f"Weekends {at}"
        return f"{', '.join(WEEKDAYS[d] for d in days)} {at}"
    if kind == "monthly":
        return f"Every month on the {_ordinal(reminder.get('monthly_day', 1))} {at}"
    if kind == "yearly":
        month = MONTHS[reminder.get("yearly_month", 1) - 1]
        return f"Every year on {month} {reminder.get('yearly_day', 1)} {at}"
    try:
        d = datetime.date.fromisoformat(reminder.get("date", ""))
        return f"Once on {MONTHS[d.month - 1]} {d.day} {at}"
    except ValueError:
        return f"Once {at}"


def group_of(when, now):
    """Which list section an occurrence belongs to."""
    days = (when.date() - now.date()).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Tomorrow"
    if days <= 6 - now.weekday():  # through Sunday of this week
        return "This week"
    return "Later"


def relative_label(when, now):
    """Short text on the right of a row: 'in 3 h', 'Tue 10:30', 'Mar 1'."""
    if when <= now:
        return "Now"
    group = group_of(when, now)
    if group == "Today":
        minutes = -int(-(when - now).total_seconds() // 60)
        return f"in {minutes} min" if minutes < 60 else f"in {minutes // 60} h"
    if group in ("Tomorrow", "This week") or (when.date() - now.date()).days < 7:
        return f"{WEEKDAYS[when.weekday()]} {when:%H:%M}"
    label = f"{MONTHS[when.month - 1]} {when.day}"
    return label if when.year == now.year else f"{label}, {when.year}"


def countdown(when, now):
    """'in 6 h 18 min', 'in 25 min', 'tomorrow at 09:00', 'in 5 days'."""
    if when <= now:
        return "now"
    minutes = -int(-(when - now).total_seconds() // 60)
    if minutes < 60:
        return f"in {minutes} min"
    if when.date() == now.date():
        h, m = divmod(minutes, 60)
        return f"in {h} h {m} min" if m else f"in {h} h"
    days = (when.date() - now.date()).days
    if days == 1:
        return f"tomorrow at {when:%H:%M}"
    return f"in {days} days"


def preview(reminder, now):
    """'Next: Mon, Nov 16 at 13:00' for the editor."""
    occ = next_occurrence(reminder, now)
    while occ is not None and occ <= now and reminder.get("recurrence_type") != "once":
        occ = next_occurrence(reminder, now, occ)
    if occ is None:
        return "This reminder will not repeat"
    if occ <= now:
        return "This time has already passed"
    return f"Next: {WEEKDAYS[occ.weekday()]}, {MONTHS[occ.month - 1]} {occ.day} at {occ:%H:%M}"
