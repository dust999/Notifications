import sys
import datetime
import os
from PyQt6 import QtWidgets, QtGui, QtCore
from utils import load_json, save_json
from fullscreen_reminder import FullscreenReminder
from add_notify_dialog import AddNotifyDialog
from notify_list_dialog import NotifyListDialog
from settings_dialog import SettingsDialog
import winreg

class NotifyApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app, config_static, config_dynamic, main_window):
        super().__init__(self._get_valid_icon(config_static["paths"]["tray_icon"]))
        self.app = app
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.main_window = main_window
        self.reminders = load_json(config_static["paths"]["notify_path"], [])
        self.backlog = load_json(config_static["paths"]["backlog_path"], [])
        self.completed_today = load_json(config_static["paths"]["completed_today_path"], [])
        self.notify_list_dialog = None
        self.setup_tray_menu()

        self.check_overdue_reminders()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(config_dynamic["settings_dialog"]["reminder_check_interval_sec"] * 1000)

        self.setToolTip(config_static["tray"]["tray_tooltip"])
        self.activated.connect(self.handle_tray_click)
        self.show()

    def _validate_reminder(self, reminder):
        return "id" in reminder and "text" in reminder

    def _get_valid_icon(self, icon_path, default_path="icons/icon.png"):
        if os.path.exists(icon_path):
            return QtGui.QIcon(icon_path)
        print(f"Warning: Icon not found at {icon_path}, using default: {default_path}")
        return QtGui.QIcon(default_path)

    def handle_tray_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_reminder_list()

    def setup_tray_menu(self):
        self.menu = QtWidgets.QMenu()
        tray_config = self.config_static["tray"]

        open_action = QtGui.QAction(
            self._get_valid_icon(self.config_static["paths"]["notify_list_window_icon"]),
            tray_config["open_reminders_action"],
            self
        )
        open_action.triggered.connect(self.show_reminder_list)
        self.menu.addAction(open_action)

        settings_action = QtGui.QAction(
            self._get_valid_icon(self.config_static["paths"]["settings_window_icon"]),
            tray_config["settings_action"],
            self
        )
        settings_action.triggered.connect(self.show_settings_dialog)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        exit_icon_path = self.config_static["paths"].get("exit_icon", self.config_static["paths"]["tray_icon"])
        exit_action = QtGui.QAction(
            self._get_valid_icon(exit_icon_path),
            tray_config["exit_action"],
            self
        )
        exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(exit_action)

        self.setContextMenu(self.menu)

    def check_overdue_reminders(self):
        now = datetime.datetime.now()
        overdue_reminders = []

        for reminder in self.reminders[:]:
            if not self._validate_reminder(reminder):
                continue

            time_str = reminder.get("time")
            date_str = reminder.get("date")
            recurring = reminder.get("recurring")

            if time_str and not recurring and date_str:
                try:
                    reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                    if reminder_datetime < now:
                        overdue_reminders.append(reminder)
                except ValueError:
                    print(f"Warning: Invalid date/time for reminder {reminder['id']}, skipping.")

        overdue_reminders.sort(key=lambda r: datetime.datetime.fromisoformat(f"{r['date']}T{r['time']}:00"))

        for reminder in overdue_reminders:
            self.show_fullscreen_reminder(reminder["text"], reminder.get("icon"))
            self.mark_reminder_completed(reminder, overdue=True)

    def show_reminder_list(self):
        self.reminders = load_json(self.config_static["paths"]["notify_path"], [])
        self.completed_today = load_json(self.config_static["paths"]["completed_today_path"], [])
        if self.notify_list_dialog is None or not self.notify_list_dialog.isVisible():
            self.notify_list_dialog = NotifyListDialog(self.reminders, self.mark_reminder_done, self.edit_reminder, self.config_static, self.config_dynamic, self.show_add_reminder_dialog, self.main_window)
            self.notify_list_dialog.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        else:
            self.notify_list_dialog.update_reminders(self.reminders)
        self.notify_list_dialog.show()
        self.notify_list_dialog.raise_()
        self.notify_list_dialog.activateWindow()

    def show_add_reminder_dialog(self, reminder_data=None):
        dialog = AddNotifyDialog(self.backlog, self.config_static, self.config_dynamic, self.main_window, reminder_data)
        dialog.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            reminder = dialog.get_notify_data()
            if reminder["text"] and self._validate_reminder(reminder):
                if reminder_data:
                    self.reminders = [r for r in self.reminders if r.get("id") != reminder_data["id"]]

                self.reminders.append(reminder)
                save_json(self.config_static["paths"]["notify_path"], self.reminders)
                if self.notify_list_dialog and self.notify_list_dialog.isVisible():
                    self.notify_list_dialog.update_reminders(self.reminders)
                else:
                    self.show_reminder_list()

    def edit_reminder(self, reminder):
        self.show_add_reminder_dialog(reminder)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self.config_static, self.config_dynamic, self.main_window, self.toggle_auto_run)
        dialog.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.config_dynamic = dialog.get_config_data()
            save_json("config_dynamic.json", self.config_dynamic)
            self.timer.setInterval(self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"] * 1000)
            self.setIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
            self.setToolTip(self.config_static["tray"]["tray_tooltip"])

    def toggle_auto_run(self, enabled):
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        script_path = os.path.abspath(sys.argv[0])
        try:
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS) as reg_key:
                if enabled:
                    winreg.SetValueEx(reg_key, "ReminderApp", 0, winreg.REG_SZ, f'"{sys.executable}" "{script_path}"')
                else:
                    winreg.DeleteValue(reg_key, "ReminderApp")
        except WindowsError:
            if enabled:
                with winreg.CreateKey(key, key_path) as reg_key:
                    winreg.SetValueEx(reg_key, "ReminderApp", 0, winreg.REG_SZ, f'"{sys.executable}" "{script_path}"')

    def mark_reminder_done(self, reminder):
        if not self._validate_reminder(reminder):
            return

        reminder_text = reminder["text"]
        if reminder_text not in [b["text"] for b in self.backlog]:
            self.backlog.append({"text": reminder_text})
            save_json(self.config_static["paths"]["backlog_path"], self.backlog)

        self.reminders = [r for r in self.reminders if r.get("id") != reminder["id"]]
        save_json(self.config_static["paths"]["notify_path"], self.reminders)

        QtWidgets.QMessageBox.information(
            self.main_window,
            self.config_static["notify_list_dialog"]["reminder_done_title"],
            self.config_static["notify_list_dialog"]["reminder_done_message"].format(reminder=reminder["text"])
        )
        if self.notify_list_dialog and self.notify_list_dialog.isVisible():
            self.notify_list_dialog.update_reminders(self.reminders)
        else:
            self.show_reminder_list()

    def mark_reminder_completed(self, reminder, overdue=False):
        if not self._validate_reminder(reminder):
            return

        now = datetime.datetime.now()
        recurring = reminder.get("recurring")

        if not recurring:
            self.reminders = [r for r in self.reminders if r.get("id") != reminder["id"]]
            save_json(self.config_static["paths"]["notify_path"], self.reminders)
            return

        completed_entry = {
            "id": reminder["id"],
            "completed_at": now.isoformat()
        }

        self.completed_today = load_json(self.config_static["paths"]["completed_today_path"], [])

        today = now.date()
        self.completed_today = [c for c in self.completed_today
                                if datetime.datetime.fromisoformat(c["completed_at"]).date() == today]

        self.completed_today.append(completed_entry)
        save_json(self.config_static["paths"]["completed_today_path"], self.completed_today)

    def check_reminders(self):
        now = datetime.datetime.now()
        self.reminders = load_json(self.config_static["paths"]["notify_path"], [])
        self.completed_today = load_json(self.config_static["paths"]["completed_today_path"], [])

        for reminder in self.reminders[:]:
            if not self._validate_reminder(reminder):
                continue

            time_str = reminder.get("time")
            date_str = reminder.get("date")
            recurring = reminder.get("recurring")
            show = False

            if time_str:
                hour, minute = map(int, time_str.split(":"))
                if recurring:
                    today_completed = [c for c in self.completed_today
                                       if c.get("id") == reminder["id"] and
                                       datetime.datetime.fromisoformat(c["completed_at"]).date() == now.date()]

                    if not today_completed and now.hour == hour and now.minute == minute:
                        show = True
                elif date_str:
                    try:
                        reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                        if (now.year == reminder_datetime.year and
                                now.month == reminder_datetime.month and
                                now.day == reminder_datetime.day and
                                now.hour == reminder_datetime.hour and
                                now.minute == reminder_datetime.minute):
                            show = True
                    except ValueError:
                        print(f"Warning: Invalid date/time for reminder {reminder['id']}, skipping.")

            if show:
                self.show_fullscreen_reminder(reminder["text"], reminder.get("icon"))
                self.mark_reminder_completed(reminder)

    def show_fullscreen_reminder(self, text, icon_path):
        reminder = FullscreenReminder(text, icon_path, self.config_static)
        reminder.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        reminder.show()

    def exit_app(self):
        self.hide()
        self.app.quit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config_static = load_json("config_static.json", {})
    config_dynamic = load_json("config_dynamic.json", {})

    tray_icon_path = config_static["paths"]["tray_icon"]
    app.setWindowIcon(QtGui.QIcon(tray_icon_path))

    main_window = QtWidgets.QMainWindow()
    main_window.setWindowIcon(QtGui.QIcon(tray_icon_path))
    main_window.hide()
    app.main_window = main_window

    tray = NotifyApp(app, config_static, config_dynamic, main_window)
    sys.exit(app.exec())