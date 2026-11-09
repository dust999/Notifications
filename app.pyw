import sys
import datetime
import os
from PyQt6 import QtWidgets, QtGui, QtCore
from utils import load_json, prepare_data_files
from data_manager import DataManager
from fullscreen_reminder import FullscreenReminder
from settings_dialog import SettingsDialog
from reminder_check import ReminderChecker
from editor import ReminderEditor
from flyout import RemindersFlyout
from calendar_window import CalendarWindow
import autostart
import schedule
import theme


class NotifyApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app, config_static, config_dynamic, main_window):
        super().__init__()
        self.app = app
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.main_window = main_window
        # Fullscreen reminders currently on screen (see show_fullscreen_reminder)
        self._popups = []
        # The flyout is created when opened and deleted when closed (saves memory)
        self.flyout = None
        # Same for the calendar window
        self.calendar = None

        # Initialize centralized data manager
        self.data_manager = DataManager(config_static)
        for kind in ("reminders", "completed"):
            self.data_manager.subscribe(kind, self._on_data_changed)

        self.setup_tray_menu()
        self._update_tray_icon()

        self.check_overdue_reminders()

        # Main reminder check timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(config_dynamic["settings_dialog"]["reminder_check_interval_sec"] * 1000)

        self.setToolTip("Notify")
        self.activated.connect(self.handle_tray_click)
        # Windows light/dark switch: recolor the tray icon (and the app when it follows the system)
        app.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        self.show()

    def _system_theme_changed(self, _scheme):
        settings = self.config_dynamic.get("settings_dialog", {})
        if settings.get("theme", "system") == "system":
            self.preview_appearance("system", settings.get("palette"), settings.get("text_size"))
        else:
            self._update_tray_icon()

    # ---------- tray ----------

    def _update_tray_icon(self):
        # Outline bell colored for the taskbar's own light/dark setting, so it's always visible
        self.setIcon(theme.tray_icon())

    def setup_tray_menu(self):
        self.menu = QtWidgets.QMenu()
        icon = lambda name: theme.icon(name, theme.c("text2"), 16)
        self.menu.addAction(icon("open-list"), "Open reminders", self.show_reminder_list)
        self.menu.addAction(icon("calendar"), "Calendar", self.show_calendar)
        self.menu.addAction(icon("add"), "New reminder", lambda: self.open_editor(None))
        self.menu.addAction(icon("settings"), "Settings", self.show_settings_dialog)
        self.menu.addSeparator()
        self.menu.addAction(icon("exit"), "Exit", self.exit_app)
        self.setContextMenu(self.menu)

    def handle_tray_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_reminder_list()

    def show_reminder_list(self, animate=True):
        """Toggle the flyout above the tray."""
        if self.flyout is not None:
            self.flyout.close()
            return
        flyout = RemindersFlyout(self)
        self.flyout = flyout
        flyout.destroyed.connect(lambda _=None, f=flyout: self._forget_flyout(f))
        flyout.place(self.geometry())
        if animate:
            flyout.fade_in()
        else:
            flyout.show()
        flyout.raise_()
        flyout.activateWindow()

    def _forget_flyout(self, flyout):
        if self.flyout is flyout:
            self.flyout = None

    def rebuild_flyout(self):
        """Re-create the open flyout so it picks up new colors and sizes."""
        if self.flyout is None:
            return
        old, self.flyout = self.flyout, None
        old.close()
        self.show_reminder_list(animate=False)

    def preview_appearance(self, mode, palette, text_size):
        """Apply theme, color and text size right away (Settings calls this on every change)."""
        settings = dict(self.config_dynamic.get("settings_dialog", {}))
        settings.update(theme=mode, palette=palette, text_size=text_size)
        apply_theme(self.app, {"settings_dialog": settings})
        self.setup_tray_menu()
        self._update_tray_icon()
        self.rebuild_flyout()
        self.rebuild_calendar()

    def _on_data_changed(self, _data):
        if self.flyout is not None:
            self.flyout.refresh()
        if self.calendar is not None:
            self.calendar.refresh()

    # ---------- calendar ----------

    def show_calendar(self, view=None, date=None):
        """Open the calendar window, or bring it to the front if it's already open."""
        if self.flyout is not None:
            self.flyout.close()
        if self.calendar is None:
            window = CalendarWindow(self)
            self.calendar = window
            window.destroyed.connect(lambda _=None, w=window: self._forget_calendar(w))
            if view:
                window.set_view(view, date)
            window.show()
        self.calendar.showNormal()
        self.calendar.raise_()
        self.calendar.activateWindow()

    def _forget_calendar(self, window):
        if self.calendar is window:
            self.calendar = None

    def rebuild_calendar(self):
        """Re-create the open calendar (new text size), keeping its view and date."""
        if self.calendar is None:
            return
        old, self.calendar = self.calendar, None
        view, date, geometry = old.view, old.date, old.geometry()
        old.close()
        self.show_calendar(view, date)
        self.calendar.setGeometry(geometry)

    # ---------- editing ----------

    def _validate_reminder(self, reminder):
        return "id" in reminder and "text" in reminder

    def open_editor(self, reminder_data=None, initial=None, parent=None, modal=True):
        """`initial`: datetime for a new reminder; `parent`: the window it opens over (the list by default).
        modal=False (the calendar): returns at once with the open dialog, which saves when accepted;
        the calendar closes it when clicked elsewhere."""
        suggestions = [b.get("text", "") for b in self.data_manager.get_backlog() if b.get("text")]
        dialog = ReminderEditor(reminder_data, suggestions, parent or self.flyout, initial)
        if not modal:
            dialog.setModal(False)
            dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.accepted.connect(lambda: self._save_from_editor(dialog, reminder_data))
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return dialog
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._save_from_editor(dialog, reminder_data)
        return None

    def _save_from_editor(self, dialog, reminder_data):
        reminder = dialog.get_data()
        if not (reminder["text"] and self._validate_reminder(reminder)):
            return
        if reminder_data:
            # If the time moved later, forget today's "shown" mark so it can fire again
            old_time, new_time = reminder_data.get("time"), reminder.get("time")
            if old_time and new_time and new_time > old_time:
                self.data_manager.remove_completed_entry(reminder_data["id"])
            self.data_manager.update_reminder(reminder_data["id"], reminder)
        else:
            self.data_manager.add_reminder(reminder)
            self.data_manager.add_to_backlog(reminder["text"])
        self._skip_if_already_due(reminder)

    # Older name, kept for anything that still calls it
    show_add_reminder_dialog = open_editor

    def _skip_if_already_due(self, reminder):
        """A recurring reminder saved after its time for today (or its day this month/year)
        has passed would pop up right away. Count the current occurrence as done, so the
        first one shown is the next one. A time equal to the current minute is left alone:
        then the user wants it now."""
        if reminder.get("recurrence_type") == "once":
            return
        now = datetime.datetime.now()
        if reminder.get("time") == now.strftime("%H:%M"):
            return
        completed = self.data_manager.get_completed()
        if self.should_show_reminder(reminder, now, set(), completed):
            self.data_manager.add_completed_entry(reminder["id"])

    def show_settings_dialog(self):
        # No parent: the flyout is re-created while Settings is open
        dialog = SettingsDialog(self.config_static, self.config_dynamic, None, self.data_manager,
                                on_preview=self.preview_appearance)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.config_dynamic = dialog.get_config_data()
            self.data_manager.update_config_dynamic(self.config_dynamic)
            self.timer.setInterval(self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"] * 1000)

    def delete_reminder(self, reminder):
        """Delete a reminder for good (user clicked the delete button and confirmed)"""
        if not self._validate_reminder(reminder):
            return
        # remove_reminder also keeps the text in the backlog for suggestions
        self.data_manager.remove_reminder(reminder["id"])

    # ---------- firing ----------

    def check_overdue_reminders(self):
        """Show one-time reminders whose time passed while the app was not running"""
        now = datetime.datetime.now()
        overdue = []
        for reminder in self.data_manager.get_reminders():
            if self._validate_reminder(reminder) and reminder.get("recurrence_type") == "once":
                occ = schedule.next_occurrence(reminder, now)
                if occ is not None and occ < now:
                    overdue.append((occ, reminder))
        for occ, reminder in sorted(overdue, key=lambda x: x[0]):
            self.show_fullscreen_reminder(reminder, occ)
            self.mark_reminder_completed(reminder)

    def mark_reminder_completed(self, reminder, overdue=False):
        """Mark a reminder as shown: one-time ones are removed, recurring ones remember today."""
        if not self._validate_reminder(reminder):
            return
        if reminder.get("recurrence_type") == "once":
            # remove_reminder also keeps the text in the backlog for suggestions
            self.data_manager.remove_reminder(reminder["id"])
        else:
            self.data_manager.add_completed_entry(reminder["id"])

    def check_reminders(self):
        """Main reminder checking logic - called periodically"""
        now = datetime.datetime.now()
        completed = self.data_manager.get_completed()
        completed_map = {c.get("id"): c.get("completed_at") for c in completed}

        for reminder in self.data_manager.get_reminders():
            if not self._validate_reminder(reminder):
                continue
            early = schedule.early_occurrence(reminder, now, completed_map.get(f"{reminder['id']}:early"))
            if early is not None:
                lead = schedule.lead_label(reminder["remind_before_days"])
                self.show_fullscreen_reminder(
                    reminder, early, f"Coming up in {lead}: "
                                     f"{schedule.WEEKDAYS[early.weekday()]}, {schedule.MONTHS[early.month - 1]} {early.day}")
                self.data_manager.add_completed_entry(f"{reminder['id']}:early")
            if self.should_show_reminder(reminder, now, set(), completed):
                occ = schedule.next_occurrence(reminder, now, completed_map.get(reminder["id"]))
                self.show_fullscreen_reminder(reminder, occ)
                self.mark_reminder_completed(reminder)

    def should_show_reminder(self, reminder, now, completed_records, completed=None):
        """Check if a reminder should be shown at the given time"""
        reminder_id = reminder.get("id")
        recurrence_type = reminder.get("recurrence_type")
        last_completed_at = None
        if completed is not None:
            for entry in completed:
                if entry.get("id") == reminder_id:
                    last_completed_at = entry.get("completed_at")
                    break
        if recurrence_type == "once":
            return ReminderChecker.one_time(reminder, now)
        elif recurrence_type == "daily":
            return ReminderChecker.daily(reminder, now, last_completed_at)
        elif recurrence_type == "weekly":
            return ReminderChecker.weekly(reminder, now, last_completed_at)
        elif recurrence_type == "monthly":
            return ReminderChecker.monthly(reminder, now, last_completed_at)
        elif recurrence_type == "yearly":
            return ReminderChecker.yearly(reminder, now, last_completed_at)
        else:
            return True

    def show_fullscreen_reminder(self, reminder, scheduled=None, note=None):
        if self.flyout is not None:
            self.flyout.close()
        popup = FullscreenReminder(reminder, scheduled, note)
        # Hold on to the window until the user closes it. A window nothing refers to
        # gets collected by Python's garbage collector and vanishes on its own.
        self._popups.append(popup)
        popup.closed.connect(lambda p=popup: self._forget_popup(p))
        popup.show()

    def _forget_popup(self, popup):
        if popup in self._popups:
            self._popups.remove(popup)

    def exit_app(self):
        # Force save all changes before exit
        self.data_manager.force_save_all()
        self.hide()
        self.app.quit()


def apply_theme(app, config_dynamic):
    settings = config_dynamic.get("settings_dialog", {})
    theme.set_mode(settings.get("theme", "system"), settings.get("palette"), settings.get("text_size"))
    app.setFont(theme.font(13))
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(theme.tile_icon())


if __name__ == "__main__":
    # Config and data files are relative paths: always run from the app folder,
    # whatever folder autostart or a shortcut launched us from.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Only one copy may run: two copies show every reminder twice and overwrite each other's files.
    instance_lock = QtCore.QLockFile(os.path.join(QtCore.QDir.tempPath(), "NotifyApp.lock"))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(100):
        QtWidgets.QMessageBox.information(None, "Notify", "Notify is already running. Look for its icon in the tray.")
        sys.exit(0)
    app.aboutToQuit.connect(instance_lock.unlock)

    autostart.repair()

    config_static = load_json("config_static.json", {})

    # Ensure config_static is a dictionary
    if not isinstance(config_static, dict):
        config_static = {}

    # The user's own data lives in user_data/, which git keeps empty.
    # Files from older versions are moved there; on a fresh copy of the app
    # they are created from the demo data in sample_data/.
    paths = config_static["paths"]
    created_from_samples = prepare_data_files([
        paths["notify_path"],
        paths["backlog_path"],
        paths["completed_path"],
        paths["config_dynamic_path"],
    ])

    config_dynamic = load_json(paths["config_dynamic_path"], {})
    apply_theme(app, config_dynamic)

    main_window = QtWidgets.QMainWindow()
    main_window.hide()

    tray = NotifyApp(app, config_static, config_dynamic, main_window)
    if paths["notify_path"] in created_from_samples:
        # Otherwise every demo reminder whose time has passed today would pop up at once
        for demo_reminder in tray.data_manager.get_reminders():
            tray._skip_if_already_due(demo_reminder)
    sys.exit(app.exec())
