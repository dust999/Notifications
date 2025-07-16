import os
from PyQt6 import QtWidgets, QtGui, QtCore
import datetime
from utils import save_json
from reminder_check import ReminderChecker


class NotifyListDialog(QtWidgets.QDialog):
    def __init__(self, reminders, mark_done_callback, edit_callback, config_static, config_dynamic, add_callback,
                 parent=None, data_manager=None):
        super().__init__(parent)
        self.reminders = reminders
        self.mark_reminder_done_callback = mark_done_callback
        self.edit_reminder_callback = edit_callback
        self.add_reminder_callback = add_callback
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.data_manager = data_manager
        self.tl_config = config_static["notify_list_dialog"]
        self.setWindowTitle(self.tl_config.get("window_title", "Reminder List"))
        icon_path = self.config_static["paths"].get("notify_list_window_icon")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        else:
            self.setWindowIcon(QtGui.QIcon(self.config_static["paths"]["tray_icon"]))

        # Применяем глобальный стиль для диалога
        self.setStyleSheet(self.config_static["notify_list_dialog"].get("stylesheet", ""))

        self.setup_ui()
        self.restore_position()

    def update_reminders(self, reminders):
        # Store current window size and position
        current_size = self.size()
        current_pos = self.pos()
        
        self.reminders = reminders
        if self.data_manager:
            completed = self.data_manager.get_completed()
        else:
            completed = []
        self.completed_ids = {c["id"] for c in completed}
        # Update UI without changing window size
        self.setup_ui()
        # Restore window size and position
        self.resize(current_size)
        self.move(current_pos)

    def get_recurrence_text(self, reminder):
        recurrence_type = reminder.get("recurrence_type")
        if recurrence_type == "daily":
            return "Daily"
        elif recurrence_type == "weekly":
            days = reminder.get("weekly_days", [])
            if not days:
                return "Weekly"
            day_names = self.config_static["add_notify_dialog"]["week_days"]
            selected_days = [day_names[day] for day in sorted(days)]
            return f"Weekly ({', '.join(selected_days)})"
        elif recurrence_type == "monthly":
            day = reminder.get("monthly_day", 1)
            return f"Monthly ({day}th)"
        elif recurrence_type == "yearly":
            month = reminder.get("yearly_month", 1)
            day = reminder.get("yearly_day", 1)
            month_names = self.config_static["add_notify_dialog"]["month_names"]
            return f"Yearly ({month_names[month - 1]} {day})"
        else:
            return "One-time"

    def is_active_daily(self, reminder, now, last_completed_at):
        if not last_completed_at:
            return True
        try:
            completed_dt = datetime.datetime.fromisoformat(last_completed_at)
            if completed_dt.date() == now.date():
                return False
        except Exception:
            return True
        return True

    def is_active_weekly(self, reminder, now, last_completed_at):
        weekly_days = reminder.get("weekly_days", [])
        current_weekday = now.weekday()
        if weekly_days and current_weekday not in weekly_days:
            return False
        if not last_completed_at:
            return True
        try:
            completed_dt = datetime.datetime.fromisoformat(last_completed_at)
            if completed_dt.date() == now.date():
                return False
        except Exception:
            return True
        return True

    def is_active_monthly(self, reminder, now, last_completed_at):
        if not last_completed_at:
            return True
        try:
            completed_dt = datetime.datetime.fromisoformat(last_completed_at)
            if completed_dt.year == now.year and completed_dt.month == now.month:
                return False
        except Exception:
            return True
        return True

    def is_active_yearly(self, reminder, now, last_completed_at):
        if not last_completed_at:
            return True
        try:
            completed_dt = datetime.datetime.fromisoformat(last_completed_at)
            if completed_dt.year == now.year:
                return False
        except Exception:
            return True
        return True

    def setup_ui(self):
        # Clear existing layout
        if self.layout() is not None:
            old_layout = self.layout()
            if old_layout is not None:
                QtWidgets.QWidget().setLayout(old_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Check if we have any reminders
        if not self.reminders:
            self.setup_empty_state(main_layout)
        else:
            self.setup_reminders_list(main_layout)

    def setup_empty_state(self, main_layout):
        """Setup UI when there are no reminders"""
        # Create a central widget for the empty state
        empty_widget = QtWidgets.QWidget()
        empty_layout = QtWidgets.QVBoxLayout(empty_widget)
        empty_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Empty state icon
        icon_label = QtWidgets.QLabel()
        icon_label.setText("📝")
        icon_label.setObjectName(self.config_static["notify_list_dialog"].get("empty_icon_class", "empty-icon"))
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_label)

        # Empty state text
        text_label = QtWidgets.QLabel("No reminders yet")
        text_label.setObjectName(self.config_static["notify_list_dialog"].get("empty_text_class", "empty-text"))
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(text_label)

        # Big Add Reminder button
        big_add_btn = QtWidgets.QPushButton("Add Your First Reminder")
        icon_path = self.config_static["paths"].get("add_notify_window_icon")
        if icon_path and os.path.exists(icon_path):
            big_add_btn.setIcon(QtGui.QIcon(icon_path))
        big_add_btn.setObjectName(self.config_static["notify_list_dialog"].get("big_add_button_class", "big-add-button"))
        big_add_btn.clicked.connect(self.add_new_reminder)
        empty_layout.addWidget(big_add_btn)

        main_layout.addWidget(empty_widget)

        # Close button at bottom
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setObjectName(self.config_static["notify_list_dialog"].get("close_button_class", "close-button"))
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)

    def setup_reminders_list(self, main_layout):
        """Setup UI when there are reminders"""
        scroll_area = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        self.notify_layout = QtWidgets.QVBoxLayout(scroll_widget)
        self.notify_layout.setSpacing(4)

        now = datetime.datetime.now()
        if self.data_manager:
            completed = self.data_manager.get_completed()
        else:
            completed = []
        completed_map = {c["id"]: c["completed_at"] for c in completed}

        sorted_reminders = []
        for reminder in self.reminders:
            time_str = reminder.get("time")
            date_str = reminder.get("date")
            if time_str:
                try:
                    recurrence_type = reminder.get("recurrence_type")
                    effective_date = now.strftime("%Y-%m-%d") if recurrence_type != "once" and not date_str else date_str
                    if effective_date:
                        dt = datetime.datetime.fromisoformat(f"{effective_date}T{time_str}:00")
                        sorted_reminders.append((reminder, dt))
                except ValueError as e:
                    print(f"Warning: Invalid date/time for reminder {reminder['id']}: {e}, skipping.")
                    continue

        # Сортировка: невыполненные сверху, выполненные снизу
        def is_completed(reminder):
            last_completed_at = completed_map.get(reminder["id"])
            recurrence_type = reminder.get("recurrence_type")
            if recurrence_type == "once":
                return last_completed_at is not None
            elif recurrence_type == "daily":
                return not self.is_active_daily(reminder, now, last_completed_at)
            elif recurrence_type == "weekly":
                return not self.is_active_weekly(reminder, now, last_completed_at)
            elif recurrence_type == "monthly":
                return not self.is_active_monthly(reminder, now, last_completed_at)
            elif recurrence_type == "yearly":
                return not self.is_active_yearly(reminder, now, last_completed_at)
            else:
                return False

        sorted_reminders.sort(key=lambda x: (is_completed(x[0]), x[1]))
        sorted_reminders = [r[0] for r in sorted_reminders]

        for i, reminder in enumerate(sorted_reminders):
            time_str = reminder.get("time")
            date_str = reminder.get("date", now.strftime("%Y-%m-%d")) if reminder.get("recurrence_type") != "once" else reminder.get("date")
            recurrence_type = reminder.get("recurrence_type")
            last_completed_at = completed_map.get(reminder["id"])
            is_completed_flag = is_completed(reminder)
            is_overdue = False
            if recurrence_type == "once" and date_str and time_str:
                try:
                    reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                    is_overdue = reminder_datetime < now and not is_completed_flag
                except ValueError:
                    print(f"Warning: Invalid date/time for overdue check on {reminder['id']}, skipping.")
                    continue

            reminder_widget = QtWidgets.QWidget()
            hbox = QtWidgets.QHBoxLayout(reminder_widget)
            hbox.setContentsMargins(12, 8, 12, 8)
            hbox.setSpacing(8)

            bg_color = "#252525" if i % 2 == 0 else "#1e1e1e"
            if is_completed_flag:
                bg_color = "#1a1a1a"
            elif is_overdue:
                bg_color = "#3e2e2e"

            reminder_widget.setObjectName(self.config_static["notify_list_dialog"].get("reminder_widget_class", "reminder-widget"))
            reminder_widget.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }} QWidget:hover {{ background-color: {'#3e3e3e' if bg_color == '#2e2e2e' else '#2e2e2e'}; }}")

            # Icon
            icon_label = QtWidgets.QLabel()
            if reminder.get("icon") and os.path.exists(reminder["icon"]):
                pixmap = QtGui.QPixmap(reminder["icon"]).scaled(20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                                                QtCore.Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText("📅")
                icon_label.setObjectName(self.config_static["notify_list_dialog"].get("icon_label_class", "icon-label"))
            icon_label.setFixedSize(24, 24)
            hbox.addWidget(icon_label)

            # Recurrence indicator
            recurrence_label = QtWidgets.QLabel()
            if recurrence_type != "once":
                if self.config_static["paths"].get("recurring_icon") and os.path.exists(
                        self.config_static["paths"]["recurring_icon"]):
                    pixmap = QtGui.QPixmap(self.config_static["paths"]["recurring_icon"]).scaled(14, 14,
                                                                                                 QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                                                                                 QtCore.Qt.TransformationMode.SmoothTransformation)
                    recurrence_label.setPixmap(pixmap)
                else:
                    recurrence_label.setText("🔄")
                    recurrence_label.setObjectName(self.config_static["notify_list_dialog"].get("recurrence_label_class", "recurrence-label"))
            recurrence_label.setFixedSize(18, 18)
            hbox.addWidget(recurrence_label)

            # Content - make it more compact
            content_layout = QtWidgets.QHBoxLayout()
            content_layout.setSpacing(8)

            # Title
            title_label = QtWidgets.QLabel(reminder["text"])
            if is_completed_flag:
                title_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #444444; }")
            elif is_overdue:
                title_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #aa5555; }")
            else:
                title_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #ffffff; }")

            # Time and recurrence info
            info_parts = [time_str]
            if recurrence_type != "once":
                info_parts.append(self.get_recurrence_text(reminder))
            elif date_str:
                info_parts.append(date_str)

            info_label = QtWidgets.QLabel(" • ".join(info_parts))
            info_label.setObjectName(self.config_static["notify_list_dialog"].get("info_label_class", "info-label"))

            content_layout.addWidget(title_label)
            content_layout.addWidget(info_label)
            content_layout.addStretch()
            hbox.addLayout(content_layout)

            # Action buttons
            button_layout = QtWidgets.QHBoxLayout()
            button_layout.setSpacing(6)

            edit_btn = QtWidgets.QPushButton()
            if self.config_static["paths"].get("edit_icon") and os.path.exists(
                    self.config_static["paths"]["edit_icon"]):
                edit_btn.setIcon(QtGui.QIcon(self.config_static["paths"]["edit_icon"]))
            else:
                edit_btn.setText("✏️")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setObjectName(self.config_static["notify_list_dialog"].get("edit_button_class", "edit-button"))
            edit_btn.setToolTip(self.tl_config["edit_tooltip"])
            edit_btn.clicked.connect(lambda _, r=reminder: self.edit_reminder(r))
            button_layout.addWidget(edit_btn)

            done_btn = QtWidgets.QPushButton()
            if self.config_static["paths"].get("delete_icon") and os.path.exists(
                    self.config_static["paths"]["delete_icon"]):
                done_btn.setIcon(QtGui.QIcon(self.config_static["paths"]["delete_icon"]))
            else:
                done_btn.setText("✓")
            done_btn.setFixedSize(28, 28)
            done_btn.setObjectName(self.config_static["notify_list_dialog"].get("done_button_class", "done-button"))
            done_btn.setToolTip(self.tl_config["delete_tooltip"])
            done_btn.clicked.connect(lambda _, r=reminder: self.mark_reminder_done(r))
            button_layout.addWidget(done_btn)

            hbox.addLayout(button_layout)
            self.notify_layout.addWidget(reminder_widget)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_layout.addWidget(scroll_area)

        # Bottom buttons
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setSpacing(8)

        add_btn = QtWidgets.QPushButton(self.tl_config["add_reminder_button"])
        icon_path = self.config_static["paths"].get("add_notify_window_icon")
        if icon_path and os.path.exists(icon_path):
            add_btn.setIcon(QtGui.QIcon(icon_path))
        add_btn.setObjectName(self.config_static["notify_list_dialog"].get("add_button_class", "add-button"))
        add_btn.setToolTip(self.tl_config["add_tooltip"])
        add_btn.clicked.connect(self.add_new_reminder)
        bottom_layout.addWidget(add_btn)

        bottom_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setObjectName(self.config_static["notify_list_dialog"].get("close_button_class", "close-button"))
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)

    def add_new_reminder(self):
        self.add_reminder_callback()

    def edit_reminder(self, reminder):
        self.edit_reminder_callback(reminder)

    def mark_reminder_done(self, reminder):
        self.mark_reminder_done_callback(reminder)

    def restore_position(self):
        """Restore window position from config"""
        try:
            pos = self.config_dynamic.get("notify_list_position", {"x": 100, "y": 100})
            self.move(pos["x"], pos["y"])
        except Exception:
            pass

    def save_position(self):
        """Save window position to config"""
        try:
            pos = {"x": self.x(), "y": self.y()}
            self.config_dynamic["notify_list_position"] = pos
            if self.data_manager:
                self.data_manager.update_config_dynamic(self.config_dynamic)
            else:
                save_json("config_dynamic.json", self.config_dynamic)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_position()
        super().closeEvent(event)

    def accept(self):
        self.save_position()
        super().accept()

    def reject(self):
        self.save_position()
        super().reject()
