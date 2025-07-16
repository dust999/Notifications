import datetime

class ReminderChecker:
    @staticmethod
    def one_time(reminder, now):
        date_str = reminder.get("date")
        time_str = reminder.get("time")
        if not date_str:
            return False
        try:
            if time_str:
                reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
            else:
                reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T00:00:00")
            return now >= reminder_datetime
        except ValueError:
            return False

    @staticmethod
    def daily(reminder, now, last_completed_at):
        time_str = reminder.get("time")
        if not time_str:
            return False
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            return False
        if not last_completed_at:
            return (now.hour, now.minute) >= (hour, minute)
        try:
            completed_dt = datetime.datetime.fromisoformat(last_completed_at)
            if completed_dt.date() == now.date():
                return False
        except Exception:
            return False
        return (now.hour, now.minute) >= (hour, minute)

    @staticmethod
    def weekly(reminder, now, last_completed_at):
        weekly_days = reminder.get("weekly_days", [])
        time_str = reminder.get("time")
        if not time_str:
            return False
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            return False
        current_weekday = now.weekday()
        if weekly_days and current_weekday not in weekly_days:
            return False
        if last_completed_at:
            try:
                completed_dt = datetime.datetime.fromisoformat(last_completed_at)
                if completed_dt.date() == now.date():
                    return False
            except Exception:
                pass
        return (now.hour, now.minute) >= (hour, minute)

    @staticmethod
    def monthly(reminder, now, last_completed_at):
        monthly_day = reminder.get("monthly_day", 1)
        time_str = reminder.get("time")
        if not time_str:
            return False
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            return False
        if last_completed_at:
            try:
                completed_dt = datetime.datetime.fromisoformat(last_completed_at)
                if completed_dt.year == now.year and completed_dt.month == now.month:
                    return False
            except Exception:
                return False
        if now.day < monthly_day:
            return False
        return (now.hour, now.minute) >= (hour, minute)

    @staticmethod
    def yearly(reminder, now, last_completed_at):
        yearly_month = reminder.get("yearly_month", 1)
        yearly_day = reminder.get("yearly_day", 1)
        time_str = reminder.get("time")
        if not time_str:
            return False
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            return False
        if last_completed_at:
            try:
                completed_dt = datetime.datetime.fromisoformat(last_completed_at)
                if completed_dt.year == now.year:
                    return False
            except Exception:
                return False
        if now.month != yearly_month:
            return False
        effective_day = ReminderChecker.get_effective_day_of_month(now.year, yearly_month, yearly_day)
        if now.day < effective_day:
            return False
        return (now.hour, now.minute) >= (hour, minute)

    @staticmethod
    def get_effective_day_of_month(year, month, day):
        try:
            if month == 12:
                next_month = datetime.datetime(year + 1, 1, 1)
            else:
                next_month = datetime.datetime(year, month + 1, 1)
            days_in_month = (next_month - datetime.timedelta(days=1)).day
            return min(day, days_in_month)
        except ValueError:
            return day 