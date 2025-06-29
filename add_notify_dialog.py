import os
from PyQt6 import QtWidgets, QtGui, QtCore
import uuid
from utils import save_json, load_json
import datetime
import calendar

class AddNotifyDialog(QtWidgets.QDialog):
    def __init__(self, backlog, config_static, config_dynamic, parent=None, reminder_data=None):
        super().__init__(parent)
        self.backlog = backlog
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.reminder_data = reminder_data
        self.at_config = config_static["add_notify_dialog"]
        self.updating = False

        if reminder_data:
            self.setWindowTitle(self.at_config.get("edit_window_title", "Edit Reminder"))
        else:
            self.setWindowTitle(self.at_config.get("window_title", "Add Reminder"))

        if self.config_static["paths"]["add_notify_window_icon"]:
            self.setWindowIcon(QtGui.QIcon(self.config_static["paths"]["add_notify_window_icon"]))

        self.setStyleSheet(self.at_config["stylesheet"])

        self.setup_ui()
        self.restore_position()
        
        # Reload backlog to ensure we have the latest data
        self.reload_backlog()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(6)

        # Set up text input field with improved autocomplete
        self.text_input = QtWidgets.QLineEdit()
        
        # Connect text changed signal for real-time suggestions
        self.text_input.textChanged.connect(self.update_suggestions)
        
        # Create completer with backlog suggestions
        self.update_suggestions()
        
        # Show suggestions when clicking on empty field
        self.text_input.mousePressEvent = self.on_text_input_click

        now = datetime.datetime.now() + datetime.timedelta(minutes=5)

        # Styles for all widgets with custom arrows and flat calendar
        icons_path = os.path.abspath("icons")
        arrow_up_path = os.path.join(icons_path, "arrow-up-white.svg").replace("\\", "/")
        arrow_down_path = os.path.join(icons_path, "arrow-down-white.svg").replace("\\", "/")
        arrow_styles = f"""
            QTimeEdit, QDateEdit, QSpinBox {{
                padding-right: 30px;
                min-height: 30px;
                font-size: 16px;
                color: #ffffff;
                background-color: #2e2e2e;
                border: 1px solid #444444;
                border-radius: 4px;
            }}
            QTimeEdit::up-button, QTimeEdit::down-button,
            QDateEdit::up-button, QDateEdit::down-button,
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 24px;
                height: 18px;
                border: none;
                background: transparent;
            }}
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover,
            QDateEdit::up-button:hover, QDateEdit::down-button:hover,
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: #444444;
            }}
            QTimeEdit::up-arrow, QDateEdit::up-arrow, QSpinBox::up-arrow {{
                width: 16px;
                height: 16px;
                image: url('{arrow_up_path}');
            }}
            QTimeEdit::down-arrow, QDateEdit::down-arrow, QSpinBox::down-arrow {{
                width: 16px;
                height: 16px;
                image: url('{arrow_down_path}');
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
                background: transparent;
            }}
            QDateEdit::down-arrow {{
                image: url('{arrow_down_path}');
                width: 16px;
                height: 16px;
            }}
            QDateEdit::down-arrow:on {{  /* when calendar is open */
                top: 1px;
                left: 1px;
            }}
            QCalendarWidget {{
                background-color: #232323;
                color: #fff;
                border: 1px solid #444444;
                border-radius: 8px;
            }}
            QCalendarWidget QToolButton {{
                background: #2e2e2e;
                color: #fff;
                border: none;
                font-size: 14px;
                font-weight: 600;
                margin: 2px;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 20px;
                min-height: 20px;
            }}
            QCalendarWidget QToolButton:hover {{
                background: #444444;
            }}
            QCalendarWidget QToolButton::menu-button {{
                border: none;
                width: 20px;
                height: 20px;
            }}
            QCalendarWidget QToolButton::menu-arrow {{
                image: url('{arrow_down_path}');
                width: 12px;
                height: 12px;
                subcontrol-position: center;
            }}
            QCalendarWidget QToolButton::up-arrow {{
                image: url('{arrow_up_path}');
                width: 12px;
                height: 12px;
                subcontrol-position: center;
            }}
            QCalendarWidget QToolButton::down-arrow {{
                image: url('{arrow_down_path}');
                width: 12px;
                height: 12px;
                subcontrol-position: center;
            }}
            QCalendarWidget QMenu {{
                background: #232323;
                color: #fff;
                border: 1px solid #444444;
            }}
            QCalendarWidget QSpinBox {{
                background: #2e2e2e;
                color: #fff;
                border: 1px solid #444444;
                border-radius: 4px;
            }}
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {{
                width: 16px;
                height: 12px;
                border: none;
                background: transparent;
            }}
            QCalendarWidget QSpinBox::up-arrow {{
                image: url('{arrow_up_path}');
                width: 12px;
                height: 12px;
            }}
            QCalendarWidget QSpinBox::down-arrow {{
                image: url('{arrow_down_path}');
                width: 12px;
                height: 12px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: #232323;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: #fff;
                background: #232323;
                selection-background-color: #0d7377;
                selection-color: #fff;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: #888;
            }}
            QCalendarWidget QAbstractItemView:selected {{
                background: #0d7377;
                color: #fff;
            }}
        """

        # Set up time input field
        self.time_input = QtWidgets.QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QtCore.QTime(now.hour, now.minute))
        self.time_input.setStyleSheet(arrow_styles)

        self.icon_combo = QtWidgets.QComboBox()
        self.icon_combo.addItem(self.at_config["no_icon_text"], "")
        for icon in self.at_config["notify_icons"]:
            icon_pixmap = QtGui.QPixmap(icon["path"]).scaled(12, 12, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.icon_combo.addItem(QtGui.QIcon(icon_pixmap), icon["name"], icon["path"])

        form_layout.addRow(self.at_config["notify_text_label"], self.text_input)
        form_layout.addRow(self.at_config["notify_time_label"], self.time_input)
        form_layout.addRow(self.at_config["notify_icon_label"], self.icon_combo)
        main_layout.addLayout(form_layout)

        recurrence_group = QtWidgets.QGroupBox(self.at_config["recurrence_label"])
        recurrence_layout = QtWidgets.QHBoxLayout()
        recurrence_layout.setSpacing(4)

        self.recurrence_buttons = {}
        for rec_type in self.at_config["recurrence_types"]:
            btn = QtWidgets.QPushButton(rec_type)
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, t=rec_type: self.update_recurrence(t) if checked and not self.updating else None)
            recurrence_layout.addWidget(btn)
            self.recurrence_buttons[rec_type] = btn

        recurrence_group.setLayout(recurrence_layout)
        main_layout.addWidget(recurrence_group)

        self.date_widget = QtWidgets.QWidget()
        date_layout = QtWidgets.QFormLayout()
        date_layout.setSpacing(4)
        self.date_input = QtWidgets.QDateEdit()
        self.date_input.setDisplayFormat("dd.MM.yy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QtCore.QDate(now.year, now.month, now.day))
        self.date_input.setStyleSheet(arrow_styles)
        date_layout.addRow(self.at_config.get("notify_date_label", "Date:"), self.date_input)
        self.date_widget.setLayout(date_layout)
        self.date_widget.setVisible(False)
        main_layout.addWidget(self.date_widget)

        self.weekly_widget = QtWidgets.QWidget()
        weekly_layout = QtWidgets.QHBoxLayout()
        weekly_layout.setSpacing(2)
        self.day_buttons = {}
        for idx, day in enumerate(self.at_config["week_days"]):
            btn = QtWidgets.QPushButton(day)
            btn.setCheckable(True)
            weekly_layout.addWidget(btn)
            self.day_buttons[idx] = btn  # Use index instead of name
        self.weekly_widget.setLayout(weekly_layout)
        self.weekly_widget.setVisible(False)
        main_layout.addWidget(self.weekly_widget)

        self.monthly_widget = QtWidgets.QWidget()
        monthly_layout = QtWidgets.QFormLayout()
        monthly_layout.setSpacing(4)
        self.monthly_day_input = QtWidgets.QSpinBox()
        self.monthly_day_input.setRange(1, 31)
        self.monthly_day_input.setValue(now.day)
        self.monthly_day_input.setStyleSheet(arrow_styles)
        monthly_layout.addRow(self.at_config["monthly_day_label"], self.monthly_day_input)
        self.monthly_widget.setLayout(monthly_layout)
        self.monthly_widget.setVisible(False)
        main_layout.addWidget(self.monthly_widget)

        self.yearly_widget = QtWidgets.QWidget()
        yearly_layout = QtWidgets.QFormLayout()
        yearly_layout.setSpacing(4)
        self.yearly_month_input = QtWidgets.QComboBox()
        self.yearly_month_input.addItems(self.at_config["month_names"])
        self.yearly_month_input.setCurrentIndex(now.month - 1)
        self.yearly_day_input = QtWidgets.QSpinBox()
        self.yearly_day_input.setRange(1, 31)
        self.yearly_day_input.setValue(now.day)
        self.yearly_day_input.setStyleSheet(arrow_styles)
        yearly_layout.addRow(self.at_config["yearly_month_label"], self.yearly_month_input)
        yearly_layout.addRow(self.at_config["yearly_day_label"], self.yearly_day_input)
        self.yearly_widget.setLayout(yearly_layout)
        self.yearly_widget.setVisible(False)
        main_layout.addWidget(self.yearly_widget)

        # Check number of days in month for yearly_day_input
        self.yearly_month_input.currentIndexChanged.connect(self.update_yearly_day_range)
        self.update_yearly_day_range()

        if self.reminder_data:
            self.text_input.setText(self.reminder_data.get("text"))
            if self.reminder_data.get("time"):
                time_parts = self.reminder_data["time"].split(":")
                self.time_input.setTime(QtCore.QTime(int(time_parts[0]), int(time_parts[1])))
            recurrence_type = self.reminder_data.get("recurrence_type")
            normalized_rec_type = next((rt for rt in self.at_config["recurrence_types"] if rt.lower() == recurrence_type.lower()), "Daily")
            self.recurrence_buttons[normalized_rec_type].setChecked(True)
            self.update_recurrence(normalized_rec_type)
            if normalized_rec_type == "One-time" and self.reminder_data.get("date"):
                date_parts = self.reminder_data["date"].split("-")
                self.date_input.setDate(QtCore.QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])))
            elif normalized_rec_type == "Weekly" and "weekly_days" in self.reminder_data:
                for idx, btn in self.day_buttons.items():
                    btn.setChecked(idx in self.reminder_data["weekly_days"])
            elif normalized_rec_type == "Monthly" and "monthly_day" in self.reminder_data:
                self.monthly_day_input.setValue(self.reminder_data["monthly_day"])
            elif normalized_rec_type == "Yearly" and "yearly_month" in self.reminder_data and "yearly_day" in self.reminder_data:
                self.yearly_month_input.setCurrentIndex(self.reminder_data["yearly_month"] - 1)
                self.yearly_day_input.setValue(self.reminder_data["yearly_day"])
            icon_path = self.reminder_data.get("icon")
            for i in range(self.icon_combo.count()):
                if self.icon_combo.itemData(i) == icon_path:
                    self.icon_combo.setCurrentIndex(i)
                    break

        main_layout.addStretch()

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText(self.at_config.get("save_button", "Save") if self.reminder_data else self.at_config.get("ok_button", "OK"))
        cancel_btn = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText(self.at_config.get("cancel_button", "Cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def on_text_input_click(self, a0):
        """Handler for clicking on the text input field to show suggestions"""
        QtWidgets.QLineEdit.mousePressEvent(self.text_input, a0)
        if not self.text_input.text().strip():
            completer = self.text_input.completer()
            if completer:
                completer.setCompletionPrefix("")
                completer.complete()

    def update_suggestions(self):
        """Update autocomplete suggestions based on current text and backlog"""
        current_text = self.text_input.text().strip()
        
        # Get suggestions from backlog
        suggestions = []
        if self.backlog:
            # If user is typing, filter by prefix; otherwise show last 5
            if current_text:
                # Filter backlog items that start with current text (case-insensitive)
                for item in self.backlog:
                    text = item.get("text", "")
                    if text and text.lower().startswith(current_text.lower()):
                        suggestions.append(text)
            else:
                # Show last 5 items from backlog
                backlog_texts = [item.get("text", "") for item in self.backlog if item.get("text")]
                suggestions = backlog_texts[-5:] if len(backlog_texts) > 5 else backlog_texts
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion.lower() not in seen:
                seen.add(suggestion.lower())
                unique_suggestions.append(suggestion)
        
        # Create and configure completer
        if unique_suggestions:
            completer = QtWidgets.QCompleter(unique_suggestions, self)
            completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
            completer.setMaxVisibleItems(5)  # Show max 5 suggestions
            self.text_input.setCompleter(completer)
        else:
            self.text_input.setCompleter(None)

    def update_recurrence(self, rec_type):
        if self.updating:
            return
        self.updating = True
        try:
            self.date_widget.setVisible(rec_type == "One-time")
            self.weekly_widget.setVisible(rec_type == "Weekly")
            self.monthly_widget.setVisible(rec_type == "Monthly")
            self.yearly_widget.setVisible(rec_type == "Yearly")
            for btn in self.recurrence_buttons.values():
                btn.setChecked(False)
            self.recurrence_buttons[rec_type].setChecked(True)
        finally:
            self.updating = False

    def update_yearly_day_range(self):
        """Update the range of days for yearly_day_input depending on the selected month"""
        month = self.yearly_month_input.currentIndex() + 1
        max_days = calendar.monthrange(2024, month)[1] if month != 2 else 29  # Всегда 29 для февраля
        self.yearly_day_input.setRange(1, max_days)
        if self.yearly_day_input.value() > max_days:
            self.yearly_day_input.setValue(max_days)

    def get_notify_data(self):
        reminder_id = self.reminder_data.get("id") if self.reminder_data else str(uuid.uuid4())
        data = {
            "id": reminder_id,
            "text": self.text_input.text().strip(),
            "time": self.time_input.time().toString("HH:mm"),
            "icon": self.icon_combo.currentData()
        }
        now = datetime.datetime.now() + datetime.timedelta(minutes=5)
        for rec_type, btn in self.recurrence_buttons.items():
            if btn.isChecked():
                data["recurrence_type"] = rec_type.lower().replace(" ", "-") if rec_type != "One-time" else "once"
                if rec_type == "One-time":
                    data["date"] = self.date_input.date().toString("yyyy-MM-dd")
                    data["recurring"] = False
                elif rec_type == "Weekly":
                    data["weekly_days"] = [idx for idx, btn in self.day_buttons.items() if btn.isChecked()]
                    data["recurring"] = True
                elif rec_type == "Monthly":
                    max_days = calendar.monthrange(now.year, now.month)[1] if now.month != 2 else 29  # Всегда 29 для февраля
                    data["monthly_day"] = min(self.monthly_day_input.value(), max_days)
                    data["recurring"] = True
                elif rec_type == "Yearly":
                    data["yearly_month"] = self.yearly_month_input.currentIndex() + 1
                    max_days = calendar.monthrange(now.year, data["yearly_month"])[1] if data["yearly_month"] != 2 else 29  # Всегда 29 для февраля
                    data["yearly_day"] = min(self.yearly_day_input.value(), max_days)
                    data["recurring"] = True
                else:
                    data["recurring"] = True
                break
        return data

    def accept(self):
        self.save_position()
        super().accept()

    def reject(self):
        self.save_position()
        super().reject()

    def restore_position(self):
        pos = self.config_dynamic["add_notify_dialog"].get("window_pos")
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
        self.config_dynamic["add_notify_dialog"]["window_pos"] = {
            "x": pos.x(),
            "y": pos.y(),
            "width": size.width(),
            "height": size.height()
        }
        save_json("config_dynamic.json", self.config_dynamic)

    def closeEvent(self, event):
        self.save_position()
        super().closeEvent(event)

    def reload_backlog(self):
        """Reload backlog data from file to ensure we have the latest suggestions"""
        try:
            backlog_path = self.config_static["paths"]["backlog_path"]
            self.backlog = load_json(backlog_path, [])
            # Update suggestions after reloading
            self.update_suggestions()
        except Exception as e:
            print(f"Error reloading backlog: {e}")