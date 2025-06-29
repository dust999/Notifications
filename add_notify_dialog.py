import os
from PyQt6 import QtWidgets, QtGui, QtCore
import uuid
from utils import save_json
import datetime

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

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(6)

        # Настройка поля ввода текста с улучшенным автокомплитом
        self.text_input = QtWidgets.QLineEdit()

        # Собираем все уникальные тексты из backlog и текущих напоминаний
        suggestions = []

        # Добавляем из backlog
        if self.backlog:
            suggestions.extend([item.get("text", "") for item in self.backlog if item.get("text")])

        # Добавляем из текущих напоминаний (если они переданы через parent)
        if hasattr(self.parent(), 'reminders') and self.parent().reminders:
            suggestions.extend([reminder.get("text", "") for reminder in self.parent().reminders if reminder.get("text")])

        # Убираем дубликаты и пустые строки
        suggestions = list(set(filter(None, suggestions)))

        if suggestions:
            completer = QtWidgets.QCompleter(suggestions, self)
            completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
            completer.setMaxVisibleItems(10)  # Показываем максимум 10 подсказок
            self.text_input.setCompleter(completer)

            # Показываем подсказки при клике на пустое поле
            self.text_input.mousePressEvent = self.on_text_input_click

        now = datetime.datetime.now() + datetime.timedelta(minutes=5)

        # Настройка поля времени с большими стрелками
        self.time_input = QtWidgets.QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QtCore.QTime(now.hour, now.minute))

        icons_path = os.path.abspath("icons")
        arrow_up_path = os.path.join(icons_path, "arrow-up-white.svg").replace("\\", "/")
        arrow_down_path = os.path.join(icons_path, "arrow-down-white.svg").replace("\\", "/")

        # Увеличиваем размер стрелок через стили
        self.time_input.setStyleSheet(f"""
            QTimeEdit {{
                padding-right: 30px;
                min-height: 25px;
                font-size: 16px;
                color: #ffffff;
                background-color: #2e2e2e;
                border: 1px solid #444444;
                border-radius: 4px;
            }}
            QTimeEdit::up-button, QTimeEdit::down-button {{
                width: 24px;
                height: 18px;
                border: none;
                background: transparent;
            }}
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{
                background-color: #444444;
            }}
            QTimeEdit::up-arrow {{
                width: 16px;
                height: 16px;
                image: url("{arrow_up_path}");
            }}
            QTimeEdit::down-arrow {{
                width: 16px;
                height: 16px;
                image: url("{arrow_down_path}");
            }}
        """)

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
            self.day_buttons[idx] = btn  # Используем индекс вместо названия
        self.weekly_widget.setLayout(weekly_layout)
        self.weekly_widget.setVisible(False)
        main_layout.addWidget(self.weekly_widget)

        self.monthly_widget = QtWidgets.QWidget()
        monthly_layout = QtWidgets.QFormLayout()
        monthly_layout.setSpacing(4)
        self.monthly_day_input = QtWidgets.QSpinBox()
        self.monthly_day_input.setRange(1, 31)
        self.monthly_day_input.setValue(now.day)
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
        yearly_layout.addRow(self.at_config["yearly_month_label"], self.yearly_month_input)
        yearly_layout.addRow(self.at_config["yearly_day_label"], self.yearly_day_input)
        self.yearly_widget.setLayout(yearly_layout)
        self.yearly_widget.setVisible(False)
        main_layout.addWidget(self.yearly_widget)

        if self.reminder_data:
            self.text_input.setText(self.reminder_data.get("text"))
            if self.reminder_data.get("time"):
                time_parts = self.reminder_data["time"].split(":")
                self.time_input.setTime(QtCore.QTime(int(time_parts[0]), int(time_parts[1])))
            recurrence_type = self.reminder_data.get("recurrence_type")
            normalized_rec_type = next((rt for rt in self.at_config["recurrence_types"] if rt.lower() == recurrence_type.lower()), "Daily")
            #self.recurrence_buttons[normalized_rec_type].setChecked(True)
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

    def on_text_input_click(self, event):
        """Обработчик клика по полю ввода текста для показа подсказок"""
        # Вызываем оригинальный обработчик
        QtWidgets.QLineEdit.mousePressEvent(self.text_input, event)

        # Если поле пустое, показываем все доступные подсказки
        if not self.text_input.text().strip():
            completer = self.text_input.completer()
            if completer:
                completer.setCompletionPrefix("")
                completer.complete()

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
                    data["monthly_day"] = self.monthly_day_input.value()
                    data["recurring"] = True
                elif rec_type == "Yearly":
                    data["yearly_month"] = self.yearly_month_input.currentIndex() + 1
                    data["yearly_day"] = self.yearly_day_input.value()
                    data["recurring"] = True
                else:
                    data["recurring"] = True
                break
        return data

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