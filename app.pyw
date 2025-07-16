import sys
import datetime
import os
from PyQt6 import QtWidgets, QtGui, QtCore
from utils import load_json, save_json
from data_manager import DataManager
from fullscreen_reminder import FullscreenReminder
from add_notify_dialog import AddNotifyDialog
from notify_list_dialog import NotifyListDialog
from settings_dialog import SettingsDialog
from reminder_check import ReminderChecker
import winreg

class NotifyApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app, config_static, config_dynamic, main_window):
        super().__init__(self._get_valid_icon(config_static["paths"]["tray_icon"]))
        self.app = app
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.main_window = main_window
        
        # Initialize centralized data manager
        self.data_manager = DataManager(config_static)
        
        # Subscribe to data changes for UI updates
        self.data_manager.subscribe('reminders', self._on_reminders_changed)
        self.data_manager.subscribe('completed_today', self._on_completed_changed)
        
        self.notify_list_dialog = None
        self.setup_tray_menu()

        self.check_overdue_reminders()

        # Main reminder check timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(config_dynamic["settings_dialog"]["reminder_check_interval_sec"] * 1000)

        self.setToolTip(config_static["tray"]["tray_tooltip"])
        self.activated.connect(self.handle_tray_click)
        self.show()

    def _on_reminders_changed(self, reminders):
        """Callback when reminders are changed"""
        if self.notify_list_dialog and self.notify_list_dialog.isVisible():
            self.notify_list_dialog.update_reminders(reminders)

    def _on_completed_changed(self, completed):
        """Callback when completed tasks are changed"""
        # You can add logic to update the UI if needed
        pass

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
        """Check for overdue one-time reminders on startup"""
        now = datetime.datetime.now()
        overdue_reminders = []
        reminders = self.data_manager.get_reminders()

        for reminder in reminders[:]:
            if not self._validate_reminder(reminder):
                continue

            # Only check one-time reminders for overdue status
            if reminder.get("recurrence_type") == "once":
                time_str = reminder.get("time")
                date_str = reminder.get("date")

                if time_str and date_str:
                    try:
                        reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                        if reminder_datetime < now:
                            overdue_reminders.append((reminder, reminder_datetime))
                    except ValueError:
                        print(f"Warning: Invalid date/time for reminder {reminder['id']}, skipping.")

        # Sort by overdue time (most overdue first)
        overdue_reminders.sort(key=lambda x: x[1])

        for reminder, _ in overdue_reminders:
            self.show_fullscreen_reminder(reminder["text"], reminder.get("icon"))
            self.mark_reminder_completed(reminder, overdue=True)

    def show_reminder_list(self):
        reminders = self.data_manager.get_reminders()
        completed = self.data_manager.get_completed()
        
        if self.notify_list_dialog is None or not self.notify_list_dialog.isVisible():
            self.notify_list_dialog = NotifyListDialog(
                reminders, 
                self.mark_reminder_done, 
                self.edit_reminder, 
                self.config_static, 
                self.config_dynamic, 
                self.show_add_reminder_dialog, 
                self.main_window,
                self.data_manager  # Передаем data_manager
            )
            self.notify_list_dialog.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        else:
            self.notify_list_dialog.update_reminders(reminders)
        self.notify_list_dialog.show()
        self.notify_list_dialog.raise_()
        self.notify_list_dialog.activateWindow()

    def show_add_reminder_dialog(self, reminder_data=None):
        backlog = self.data_manager.get_backlog()
        dialog = AddNotifyDialog(backlog, self.config_static, self.config_dynamic, self.main_window, reminder_data, self.data_manager)
        dialog.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            reminder = dialog.get_notify_data()
            if reminder["text"] and self._validate_reminder(reminder):
                if reminder_data:
                    # Update existing reminder (preserve completed entries)
                    old_time = reminder_data.get("time")
                    new_time = reminder.get("time")
                    
                    # If time changed to a later time, remove from completed_today to allow re-triggering
                    if old_time != new_time and old_time and new_time:
                        try:
                            old_hour, old_minute = map(int, old_time.split(":"))
                            new_hour, new_minute = map(int, new_time.split(":"))
                            
                            # Convert to minutes for easy comparison
                            old_minutes = old_hour * 60 + old_minute
                            new_minutes = new_hour * 60 + new_minute
                            
                            # Only reset if new time is later than old time
                            if new_minutes > old_minutes:
                                self.data_manager.remove_completed_entry(reminder_data["id"])
                        except ValueError:
                            # If time format is invalid, don't reset
                            pass
                    
                    self.data_manager.update_reminder(reminder_data["id"], reminder)
                else:
                    # Add new reminder
                    self.data_manager.add_reminder(reminder)
                    # Add to backlog when creating new notification (not when editing)
                    self.data_manager.add_to_backlog(reminder["text"])
                
                if self.notify_list_dialog and self.notify_list_dialog.isVisible():
                    # UI will update automatically via callback
                    pass
                else:
                    self.show_reminder_list()

    def edit_reminder(self, reminder):
        self.show_add_reminder_dialog(reminder)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self.config_static, self.config_dynamic, self.main_window, self.toggle_auto_run)
        dialog.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.config_dynamic = dialog.get_config_data()
            self.data_manager.update_config_dynamic(self.config_dynamic)
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
        """Manually mark a reminder as done (user clicked the done button)"""
        if not self._validate_reminder(reminder):
            return

        reminder_id = reminder["id"]
        reminder_text = reminder["text"]

        # Always remove the reminder when delete button is clicked
        # 1. Add to backlog for history
        self.data_manager.add_to_backlog(reminder_text)
        # 2. Remove from notifications
        self.data_manager.remove_reminder(reminder_id)

        if self.notify_list_dialog and self.notify_list_dialog.isVisible():
            # UI will update automatically via callback
            pass
        else:
            self.show_reminder_list()

    def mark_reminder_completed(self, reminder, overdue=False):
        """Mark a reminder as completed and handle file updates"""
        if not self._validate_reminder(reminder):
            return

        reminder_id = reminder["id"]
        reminder_text = reminder["text"]
        recurrence_type = reminder.get("recurrence_type")

        if recurrence_type == "once":
            # For one-time reminders:
            # 1. Add to backlog
            self.data_manager.add_to_backlog(reminder_text)
            # 2. Remove from notifications
            self.data_manager.remove_reminder(reminder_id)
        else:
            # For recurring reminders, just mark as completed today
            self.data_manager.add_completed_entry(reminder_id)

    def check_reminders(self):
        """Main reminder checking logic - called periodically"""
        now = datetime.datetime.now()
        reminders = self.data_manager.get_reminders()
        completed = self.data_manager.get_completed()
        completed_records = {c["id"] for c in completed}

        for reminder in reminders[:]:
            if not self._validate_reminder(reminder):
                continue

            should_show = self.should_show_reminder(reminder, now, completed_records, completed)
            if should_show:
                self.show_fullscreen_reminder(reminder["text"], reminder.get("icon"))
                self.mark_reminder_completed(reminder)

    def should_show_reminder(self, reminder, now, completed_records, completed=None):
        """Check if a reminder should be shown at the given time, передаёт дату последнего показа в методы проверок"""
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

    def show_fullscreen_reminder(self, text, icon_path):
        reminder = FullscreenReminder(text, icon_path, self.config_static)
        reminder.setWindowIcon(self._get_valid_icon(self.config_static["paths"]["tray_icon"]))
        reminder.show()

    def exit_app(self):
        # Force save all changes before exit
        self.data_manager.force_save_all()
        
        self.hide()
        self.app.quit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config_static = load_json("config_static.json", {})
    config_dynamic = load_json("config_dynamic.json", {})
    
    # Ensure config_static is a dictionary
    if not isinstance(config_static, dict):
        config_static = {}

    # Safely get tray icon path with fallback
    tray_icon_path = config_static.get("paths", {}).get("tray_icon", "icons/icon.png")
    app.setWindowIcon(QtGui.QIcon(tray_icon_path))

    main_window = QtWidgets.QMainWindow()
    main_window.setWindowIcon(QtGui.QIcon(tray_icon_path))
    main_window.hide()

    tray = NotifyApp(app, config_static, config_dynamic, main_window)
    sys.exit(app.exec())