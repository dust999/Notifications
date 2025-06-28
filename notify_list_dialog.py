import os
from PyQt6 import QtWidgets, QtGui, QtCore
import datetime
from utils import save_json

class NotifyListDialog(QtWidgets.QDialog):
    def __init__(self, reminders, mark_done_callback, edit_callback, config_static, config_dynamic, add_callback, parent=None):
        super().__init__(parent)
        self.reminders = reminders
        self.mark_reminder_done_callback = mark_done_callback
        self.edit_reminder_callback = edit_callback
        self.add_reminder_callback = add_callback
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.tl_config = config_static["notify_list_dialog"]
        self.setWindowTitle(self.tl_config.get("window_title", "Reminder List"))
        icon_path = self.config_static["paths"].get("notify_list_window_icon")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        else:
            self.setWindowIcon(QtGui.QIcon(self.config_static["paths"]["tray_icon"]))

        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI'; }
            QPushButton { background-color: #2e2e2e; border: 1px solid #444444; border-radius: 6px; padding: 8px 16px; color: #ffffff; font-weight: 500; }
            QPushButton:hover { background-color: #3e3e3e; border-color: #555555; }
            QPushButton:pressed { background-color: #1e1e1e; }
            QScrollArea { border: 1px solid #2e2e2e; border-radius: 8px; background-color: #1e1e1e; }
            QScrollBar:vertical { background: none; width: 12px; margin: 0; }
            QScrollBar::handle:vertical { background-color: #0d7377; min-height: 20px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background-color: #1a8c99; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
            QScrollBar::add-page, QScrollBar::sub-page { background: none; }
        """)

        self.setup_ui()
        self.restore_position()

    def update_reminders(self, reminders):
        self.reminders = reminders
        self.completed_today = self.config_dynamic.get("completed_today", [])
        while self.notify_layout.count():
            item = self.notify_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.setup_ui()
        self.show()

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
            return f"Yearly ({month_names[month-1]} {day})"
        else:
            return "One-time"

    def setup_ui(self):
        if self.layout() is not None:
            old_layout = self.layout()
            if old_layout is not None:
                QtWidgets.QWidget().setLayout(old_layout)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        scroll_area = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        self.notify_layout = QtWidgets.QVBoxLayout(scroll_widget)
        self.notify_layout.setSpacing(4)

        now = datetime.datetime.now()
        completed_today_ids = {c["id"] for c in self.config_dynamic.get("completed_today", []) if datetime.datetime.fromisoformat(c["completed_at"]).date() == now.date()}

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

        sorted_reminders.sort(key=lambda x: (0 if x[0]["id"] in completed_today_ids else 1, x[1]))
        sorted_reminders = [r[0] for r in sorted_reminders]

        for i, reminder in enumerate(sorted_reminders):
            time_str = reminder.get("time")
            date_str = reminder.get("date", now.strftime("%Y-%m-%d")) if reminder.get("recurrence_type") != "once" else reminder.get("date")
            recurrence_type = reminder.get("recurrence_type")
            is_overdue = False
            is_completed = reminder["id"] in completed_today_ids

            if recurrence_type == "once" and date_str and time_str:
                try:
                    reminder_datetime = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                    is_overdue = reminder_datetime < now
                except ValueError:
                    print(f"Warning: Invalid date/time for overdue check on {reminder['id']}, skipping.")
                    continue

            reminder_widget = QtWidgets.QWidget()
            hbox = QtWidgets.QHBoxLayout(reminder_widget)
            hbox.setContentsMargins(12, 8, 12, 8)
            hbox.setSpacing(8)

            bg_color = "#2e2e2e" if i % 2 == 0 else "#1e1e1e"
            if is_completed:
                bg_color = "#2a2a2a"
            elif is_overdue:
                bg_color = "#3e2e2e"

            reminder_widget.setStyleSheet(f"""
                QWidget {{ background-color: {bg_color}; border-radius: 6px; margin: 1px; }}
                QWidget:hover {{ background-color: {bg_color.replace('#', '#')} if not is_completed else bg_color; }}
            """)

            icon_label = QtWidgets.QLabel()
            if reminder.get("icon") and os.path.exists(reminder["icon"]):
                pixmap = QtGui.QPixmap(reminder["icon"]).scaled(20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText("📅")
                icon_label.setStyleSheet("font-size: 16px;")
            icon_label.setFixedSize(24, 24)
            hbox.addWidget(icon_label)

            recurrence_label = QtWidgets.QLabel()
            if recurrence_type != "once":
                if self.config_static["paths"].get("recurring_icon") and os.path.exists(self.config_static["paths"]["recurring_icon"]):
                    pixmap = QtGui.QPixmap(self.config_static["paths"]["recurring_icon"]).scaled(14, 14, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                    recurrence_label.setPixmap(pixmap)
                else:
                    recurrence_label.setText("🔄")
                    recurrence_label.setStyleSheet("font-size: 12px;")
            recurrence_label.setFixedSize(18, 18)
            hbox.addWidget(recurrence_label)

            content_layout = QtWidgets.QVBoxLayout()
            content_layout.setSpacing(0)

            title_label = QtWidgets.QLabel(reminder["text"])
            title_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #ffffff; }")
            if is_completed:
                title_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #888888; text-decoration: line-through; }")
            elif is_overdue:
                title_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #aa5555; }")

            info_parts = [time_str]
            if recurrence_type != "once":
                info_parts.append(self.get_recurrence_text(reminder))
            elif date_str:
                info_parts.append(date_str)

            info_label = QtWidgets.QLabel(" • ".join(info_parts))
            info_label.setStyleSheet("QLabel { font-size: 10px; color: #aaaaaa; }")
            if is_completed:
                info_label.setStyleSheet("QLabel { font-size: 10px; color: #888888; }")

            content_layout.addWidget(title_label)
            content_layout.addWidget(info_label)
            hbox.addLayout(content_layout)
            hbox.addStretch()

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.setSpacing(6)

            edit_btn = QtWidgets.QPushButton()
            if self.config_static["paths"].get("edit_icon") and os.path.exists(self.config_static["paths"]["edit_icon"]):
                edit_btn.setIcon(QtGui.QIcon(self.config_static["paths"]["edit_icon"]))
            else:
                edit_btn.setText("✏️")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setStyleSheet("QPushButton { background-color: #3e3e3e; border: 1px solid #444444; border-radius: 4px; padding: 4px; } QPushButton:hover { background-color: #4e4e4e; }")
            edit_btn.setToolTip(self.tl_config["edit_tooltip"])
            edit_btn.clicked.connect(lambda _, r=reminder: self.edit_reminder(r))
            button_layout.addWidget(edit_btn)

            complete_btn = QtWidgets.QPushButton()
            if self.config_static["paths"].get("delete_icon") and os.path.exists(self.config_static["paths"]["delete_icon"]):
                complete_btn.setIcon(QtGui.QIcon(self.config_static["paths"]["delete_icon"]))
            else:
                complete_btn.setText("✓")
            complete_btn.setFixedSize(28, 28)
            complete_btn.setStyleSheet("QPushButton { background-color: #2e2e2e; border: 1px solid #444444; border-radius: 4px; padding: 4px; } QPushButton:hover { background-color: #3e3e3e; }")
            complete_btn.setToolTip(self.tl_config["delete_tooltip"])
            complete_btn.clicked.connect(lambda _, r=reminder: self.mark_reminder_done(r))
            button_layout.addWidget(complete_btn)

            hbox.addLayout(button_layout)
            self.notify_layout.addWidget(reminder_widget)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)
        main_layout.addWidget(scroll_area)

        # Кнопки внизу в одной строке
        bottom_layout = QtWidgets.QHBoxLayout()

        # Кнопка Add Reminder слева
        self.add_reminder_btn = QtWidgets.QPushButton()
        icon_path = self.config_static["paths"].get("add_notify_window_icon")
        if icon_path and os.path.exists(icon_path):
            self.add_reminder_btn.setIcon(QtGui.QIcon(icon_path))
        self.add_reminder_btn.setText(self.tl_config["add_reminder_button"])
        self.add_reminder_btn.setStyleSheet("QPushButton { background-color: #0d7377; border: 1px solid #1a8c99; font-weight: 600; } QPushButton:hover { background-color: #1a8c99; } QPushButton:pressed { background-color: #0a5d61; }")
        self.add_reminder_btn.clicked.connect(self.add_new_reminder)
        bottom_layout.addWidget(self.add_reminder_btn)

        # Растягивающееся пространство между кнопками
        bottom_layout.addStretch()

        # Кнопка Close справа
        close_btn = QtWidgets.QPushButton()
        close_btn.setText(self.tl_config.get("close_button", "Close"))
        close_btn.setStyleSheet("QPushButton { background-color: #3e3e3e; border: 1px solid #444444; min-width: 80px; } QPushButton:hover { background-color: #4e4e4e; }")
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)

        main_layout.addLayout(bottom_layout)

    def add_new_reminder(self):
        self.add_reminder_callback()

    def edit_reminder(self, reminder):
        self.edit_reminder_callback(reminder)

    def mark_reminder_done(self, reminder):
        self.mark_reminder_done_callback(reminder)
        for i in range(self.notify_layout.count()):
            widget = self.notify_layout.itemAt(i).widget()
            if widget:
                layout = widget.layout()
                if layout and layout.itemAt(2):
                    content_layout = layout.itemAt(2)
                    if content_layout and content_layout.itemAt(0):
                        title_widget = content_layout.itemAt(0).widget()
                        if title_widget and isinstance(title_widget, QtWidgets.QLabel):
                            if title_widget.text() == reminder["text"]:
                                widget.setParent(None)
                                break

    def restore_position(self):
        pos = self.config_dynamic["notify_list_dialog"].get("window_pos")
        if pos:
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            x = min(pos.get("x", 0), screen.width() - pos.get("width", self.width()))
            y = max(0, min(pos.get("y", 0), screen.height() - pos.get("height", self.height())))
            self.move(x, y)
            if "width" in pos and "height" in pos:
                self.resize(pos["width"], pos["height"])

    def save_position(self):
        pos = self.pos()
        size = self.size()
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.config_dynamic["notify_list_dialog"]["window_pos"] = {
            "x": pos.x(),
            "y": pos.y(),
            "width": size.width(),
            "height": size.height()
        }
        save_json("config_dynamic.json", self.config_dynamic)

    def closeEvent(self, event):
        self.save_position()
        super().closeEvent(event)