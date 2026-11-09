"""New reminder / Edit reminder dialog."""
import calendar
import datetime
import uuid

from PyQt6 import QtCore, QtWidgets

import schedule
import theme
from widgets import ColorSwatch, DatePopup, GlassDialog, IconButton, Segmented, divider, label

REPEATS = ["once", "daily", "weekly", "monthly", "yearly"]
CATEGORY_ICONS = {"work": "icons/work.png", "personal": "icons/home.png",
                  "health": "icons/health.png", "shopping": "icons/shopping.png", "none": ""}


class ReminderEditor(GlassDialog):
    def __init__(self, reminder=None, suggestions=(), parent=None, initial=None):
        """`initial`: a datetime to start a new reminder at (the calendar passes the clicked day/time)."""
        super().__init__(parent)
        self.initial = initial
        self.reminder = reminder
        self.setFixedWidth(theme.px(470))
        self.setWindowTitle("Edit reminder" if reminder else "New reminder")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(6)

        head = QtWidgets.QHBoxLayout()
        head.addWidget(label(self.windowTitle(), "h2"))
        head.addStretch()
        close = IconButton("close", "Close", 32, 18)
        close.clicked.connect(self.reject)
        head.addWidget(close)
        root.addLayout(head)
        root.addSpacing(6)

        root.addWidget(label("Title", "field"))
        self.title = QtWidgets.QLineEdit()
        self.title.setPlaceholderText("What do you want to remember?")
        completer = QtWidgets.QCompleter(sorted(set(suggestions), key=str.lower), self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.popup().setObjectName("suggestions")
        self.title.setCompleter(completer)
        self.title.textChanged.connect(lambda: self._set_error(""))
        root.addWidget(self.title)
        self.error = label("", "error")
        self.error.hide()
        root.addWidget(self.error)

        root.addSpacing(6)
        root.addWidget(label("Time", "field"))
        self.time = QtWidgets.QTimeEdit()
        self.time.setDisplayFormat("HH:mm")
        self.time.setFixedWidth(theme.px(140))
        self.time.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        root.addWidget(self.time)

        root.addSpacing(6)
        root.addWidget(label("Repeat", "field"))
        self.repeat = Segmented(["Once", "Daily", "Weekly", "Monthly", "Yearly"])
        root.addWidget(self.repeat)

        # Only the fields the chosen repeat needs are shown
        self.date = QtWidgets.QDateEdit()
        self.date.setDisplayFormat("dd.MM.yyyy")
        # Typing works; the calendar button next to it opens our own month picker
        self.date.setCalendarPopup(False)
        self.date.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.date.setMinimumWidth(theme.px(160))  # room for the full year and the popup arrow
        self.days = QtWidgets.QWidget()
        days_lay = QtWidgets.QHBoxLayout(self.days)
        days_lay.setContentsMargins(0, 0, 0, 0)
        days_lay.setSpacing(4)
        self.day_buttons = []
        for i, name in enumerate(schedule.WEEKDAYS):
            b = QtWidgets.QPushButton(name)
            b.setProperty("kind", "chip")
            # Focus only from the keyboard: a clicked chip kept the focus border, which looks
            # exactly like "selected", so a chip switched off still seemed on
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            b.setCheckable(True)
            b.setAccessibleName(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][i])
            b.toggled.connect(self._update_preview)
            self.day_buttons.append(b)
        for i in schedule.week_order():  # shown from the first day of the week (Monday or Sunday)
            days_lay.addWidget(self.day_buttons[i])
        self.month_day = QtWidgets.QSpinBox()
        self.month_day.setRange(1, 31)
        self.month_day.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.month_day.setFixedWidth(theme.px(80))
        self.month_note = label("On shorter months: last day", "meta")
        self.year_month = QtWidgets.QComboBox()
        self.year_month.addItems(schedule.MONTHS)
        self.year_day = QtWidgets.QSpinBox()
        self.year_day.setRange(1, 31)
        self.year_day.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.year_day.setFixedWidth(theme.px(80))

        once_pick = self._calendar_button(lambda: self._pick_once_date())
        month_pick = self._calendar_button(lambda: self._pick_monthly_day())
        year_pick = self._calendar_button(lambda: self._pick_yearly_date())
        self._pickers = [(once_pick, self.date), (month_pick, self.month_day), (year_pick, self.year_day)]

        self.detail = {}
        for kind, widgets in (("once", [self.date, once_pick]), ("weekly", [self.days]),
                              ("monthly", [self.month_day, month_pick, self.month_note]),
                              ("yearly", [self.year_month, self.year_day, year_pick])):
            box = QtWidgets.QWidget()
            lay = QtWidgets.QHBoxLayout(box)
            lay.setContentsMargins(0, 6, 0, 0)
            lay.setSpacing(8)
            for w in widgets:
                lay.addWidget(w)
            if kind != "weekly":
                lay.addStretch()
            self.detail[kind] = box
            root.addWidget(box)

        root.addSpacing(6)
        root.addWidget(label("Category", "field"))
        cats = QtWidgets.QHBoxLayout()
        cats.setSpacing(4)
        self.cat_group = QtWidgets.QButtonGroup(self)
        for i, cat in enumerate(schedule.CATEGORIES):
            b = QtWidgets.QPushButton(schedule.CATEGORY_NAMES[cat])
            b.setProperty("kind", "chip")
            # Focus only from the keyboard: a clicked chip kept the focus border, which looks
            # exactly like "selected", so a chip switched off still seemed on
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            b.setCheckable(True)
            if cat != "none":
                b.setIcon(theme.icon(f"cat-{cat}", theme.c("cat")[cat][0], theme.px(16)))
                b.setIconSize(QtCore.QSize(theme.px(16), theme.px(16)))
            self.cat_group.addButton(b, i)
            cats.addWidget(b)
        root.addLayout(cats)

        # Color: makes a reminder stand out in the calendar (payday green, bills red...)
        root.addSpacing(6)
        root.addWidget(label("Color", "field"))
        colors = QtWidgets.QHBoxLayout()
        colors.setSpacing(theme.px(4))
        self.color_group = QtWidgets.QButtonGroup(self)
        self.color_names = [None] + [key for key, *_ in theme.REMINDER_COLORS]
        tips = ["No color"] + [name for _, name, *_ in theme.REMINDER_COLORS]
        for i, (key, tip) in enumerate(zip(self.color_names, tips)):
            swatch = ColorSwatch(key, tip)
            self.color_group.addButton(swatch, i)
            colors.addWidget(swatch)
        colors.addStretch()
        root.addLayout(colors)

        self.earlier_box = QtWidgets.QWidget()
        eb = QtWidgets.QVBoxLayout(self.earlier_box)
        eb.setContentsMargins(0, 6, 0, 0)
        eb.setSpacing(6)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(label("Remind me earlier", "field"))
        head.addWidget(label("pick any, plus the day itself", "meta"))
        head.addStretch()
        eb.addLayout(head)
        # Independent chips: every one switched on sends its own heads-up
        leads = QtWidgets.QHBoxLayout()
        leads.setSpacing(4)
        self.lead_buttons = {}
        for days in schedule.LEAD_DAYS:
            b = QtWidgets.QPushButton(schedule.lead_label(days))
            b.setProperty("kind", "chip")
            # Focus only from the keyboard: a clicked chip kept the focus border, which looks
            # exactly like "selected", so a chip switched off still seemed on
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            b.setCheckable(True)
            b.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            b.toggled.connect(self._update_preview)
            self.lead_buttons[days] = b
            leads.addWidget(b)
        leads.addStretch()
        eb.addLayout(leads)
        root.addWidget(self.earlier_box)

        root.addSpacing(10)
        root.addWidget(divider())
        prev = QtWidgets.QHBoxLayout()
        prev.setContentsMargins(0, 8, 0, 8)
        clock = QtWidgets.QLabel()
        clock.setPixmap(theme.pixmap("clock", theme.c("text2"), theme.px(16)))
        prev.addWidget(clock)
        self.preview = label("", "meta")
        self.preview.setWordWrap(True)  # several heads-ups make a long line
        prev.addWidget(self.preview, 1)
        root.addLayout(prev)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QtWidgets.QPushButton("Save")
        save.setProperty("kind", "primary")
        save.setDefault(True)
        save.setMinimumWidth(theme.px(96))
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self._load(reminder)
        for signal in (self.repeat.changed, self.time.timeChanged, self.date.dateChanged,
                       self.month_day.valueChanged, self.year_month.currentIndexChanged,
                       self.year_day.valueChanged):
            signal.connect(self._update_preview)
        self.repeat.changed.connect(self._show_details)
        self._show_details()
        self.title.setFocus()

    # ----- load / collect -----

    def _load(self, r):
        soon = self.initial or datetime.datetime.now() + datetime.timedelta(minutes=5)
        r = r or {}
        self.title.setText(r.get("text", ""))
        t = schedule._time_of(r) or soon.time()
        self.time.setTime(QtCore.QTime(t.hour, t.minute))
        kind = r.get("recurrence_type", "once")
        self.repeat.set_index(REPEATS.index(kind) if kind in REPEATS else 0)
        try:
            d = datetime.date.fromisoformat(r.get("date", ""))
        except ValueError:
            d = soon.date()
        self.date.setDate(QtCore.QDate(d.year, d.month, d.day))
        for i in r.get("weekly_days", [soon.weekday()]):
            self.day_buttons[i].setChecked(True)
        self.month_day.setValue(r.get("monthly_day", soon.day))
        self.year_month.setCurrentIndex(r.get("yearly_month", soon.month) - 1)
        self.year_day.setValue(r.get("yearly_day", soon.day))
        self.cat_group.button(schedule.CATEGORIES.index(schedule.category_of(r))).setChecked(True)
        color = r.get("color")
        self.color_group.button(self.color_names.index(color) if color in self.color_names else 0).setChecked(True)
        for days in schedule.leads_of(r):
            if days in self.lead_buttons:
                self.lead_buttons[days].setChecked(True)

    def get_data(self):
        kind = REPEATS[self.repeat.index()]
        cat = schedule.CATEGORIES[self.cat_group.checkedId()]
        data = {
            "id": (self.reminder or {}).get("id") or str(uuid.uuid4()),
            "text": self.title.text().strip(),
            "time": self.time.time().toString("HH:mm"),
            "icon": CATEGORY_ICONS[cat],
            "category": cat,
            "recurrence_type": kind,
            "recurring": kind != "once",
        }
        if kind == "once":
            data["date"] = self.date.date().toString("yyyy-MM-dd")
        elif kind == "weekly":
            data["weekly_days"] = [i for i, b in enumerate(self.day_buttons) if b.isChecked()]
        elif kind == "monthly":
            data["monthly_day"] = self.month_day.value()
        elif kind == "yearly":
            data["yearly_month"] = self.year_month.currentIndex() + 1
            data["yearly_day"] = self.year_day.value()
        leads = [d for d, b in sorted(self.lead_buttons.items(), reverse=True) if b.isChecked()]
        if kind in ("once", "monthly", "yearly") and leads:
            data["remind_before_days"] = leads
        color = self.color_names[max(self.color_group.checkedId(), 0)]
        if color:
            data["color"] = color
        return data

    # ----- picking a date in a calendar -----

    def _calendar_button(self, handler):
        b = IconButton("calendar", "Pick a date in the calendar", 36, 20)
        b.setProperty("kind", "tool")
        self.date.ensurePolished()
        side = max(self.date.sizeHint().height(), theme.px(36))
        b._side = side
        b.setFixedSize(side, side)
        b.clicked.connect(handler)
        return b

    def showEvent(self, event):
        # Square calendar buttons exactly as tall as the field next to them (known once styled)
        for button, field in self._pickers:
            side = field.sizeHint().height()
            button._side = side
            button.setFixedSize(side, side)
        super().showEvent(event)

    def _pick_once_date(self):
        q = self.date.date()
        popup = DatePopup(datetime.date(q.year(), q.month(), q.day()), self)
        popup.picked.connect(lambda d: self.date.setDate(QtCore.QDate(d.year, d.month, d.day)))
        popup.show_under(self.date)

    def _pick_monthly_day(self):
        """Only the day of the month matters: open on its next date, take the day that's clicked."""
        today = datetime.date.today()
        day = self.month_day.value()
        clamp = lambda d: d.replace(day=min(day, calendar.monthrange(d.year, d.month)[1]))
        start = clamp(today)
        if start < today:
            start = clamp((today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1))
        popup = DatePopup(start, self)
        popup.picked.connect(lambda d: self.month_day.setValue(d.day))
        popup.show_under(self.month_day)

    def _pick_yearly_date(self):
        """The year doesn't matter for a yearly reminder: open on its next date, keep month and day."""
        today = datetime.date.today()
        month, day = self.year_month.currentIndex() + 1, self.year_day.value()
        clamp = lambda y: datetime.date(y, month, min(day, calendar.monthrange(y, month)[1]))
        start = clamp(today.year) if clamp(today.year) >= today else clamp(today.year + 1)
        popup = DatePopup(start, self)
        popup.picked.connect(lambda d: (self.year_month.setCurrentIndex(d.month - 1), self.year_day.setValue(d.day)))
        popup.show_under(self.year_month)

    # ----- behaviour -----

    def _show_details(self):
        kind = REPEATS[self.repeat.index()]
        for k, box in self.detail.items():
            box.setVisible(k == kind)
        self.adjustSize()
        self._update_preview()

    def _update_earlier(self):
        """Show only the heads-up options that make sense for the current repeat, date and time."""
        data = self.get_data()
        data.pop("remind_before_days", None)
        allowed = schedule.lead_choices(data, datetime.datetime.now())
        for days, button in self.lead_buttons.items():
            button.setVisible(days in allowed)
            if days not in allowed and button.isChecked():
                button.blockSignals(True)
                button.setChecked(False)  # no longer fits (e.g. "1 month" for a monthly reminder)
                button.blockSignals(False)
        if self.earlier_box.isHidden() == bool(allowed):
            self.earlier_box.setVisible(bool(allowed))
            self._fit_later()

    def _update_preview(self):
        self._update_earlier()
        data = self.get_data()
        if data["recurrence_type"] == "weekly" and not data["weekly_days"]:
            self.preview.setText("Choose at least one day")
            return
        text = schedule.preview(data, datetime.datetime.now())
        leads = schedule.leads_of(data)
        if leads:
            text += f", plus {'a heads-up' if len(leads) == 1 else 'heads-ups'} {schedule.leads_text(leads)} before"
        self.preview.setText(text)
        self._fit_later()

    def _fit_later(self):
        """Grow or shrink to the content once the layout has settled. Without this a preview
        that wraps to a second line squeezed the rows above it (the heads-up chips)."""
        QtCore.QTimer.singleShot(0, self._fit)

    def _fit(self):
        layout = self.layout()
        need = layout.totalHeightForWidth(self.width()) if layout.hasHeightForWidth() else layout.totalSizeHint().height()
        if need > 0 and need != self.height():
            self.resize(self.width(), need)

    def _set_error(self, text):
        self.error.setText(text)
        self.error.setVisible(bool(text))
        self.title.setProperty("invalid", bool(text))
        self.title.style().unpolish(self.title)
        self.title.style().polish(self.title)

    def _save(self):
        data = self.get_data()
        if not data["text"]:
            self._set_error("Enter a title")
            self.title.setFocus()
            return
        if data["recurrence_type"] == "weekly" and not data["weekly_days"]:
            self.preview.setText("Choose at least one day")
            return
        self.accept()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self._save()
        else:
            super().keyPressEvent(event)
