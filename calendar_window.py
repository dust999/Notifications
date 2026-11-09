"""Calendar window: Day, Month and Year views of all reminders. Click a day or a time to add one.

Each view is painted by one widget (CalendarCanvas) with its own hit-testing: no widget per day
or per reminder, so the window stays light. It is created when opened and destroyed when closed.
Layout follows design/calendar.html (approved mockup) and design/CALENDAR-NOTES.md.
"""
import calendar
import datetime

from PyQt6 import QtCore, QtGui, QtWidgets

import schedule
import theme
from widgets import IconButton, Segmented, label

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
VIEWS = ["day", "month", "year"]
NEW_AT = datetime.time(9, 0)  # time for a reminder created by clicking a day
HINTS = {"day": "Click a time to add a reminder",
         "month": "Click a day to add a reminder, or its number to open the day",
         "year": "Click a day to open it"}


def shift_month(d, n):
    """The same day n months later (or earlier), clamped to the month's length."""
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    return datetime.date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1]))


def _col(name, alpha=None):
    col = theme.qcolor(theme.c(name))
    if alpha is not None:
        col.setAlphaF(alpha)
    return col


def _cat_colors(reminder):
    symbol, tint = theme.c("cat")[schedule.category_of(reminder)]
    return theme.qcolor(symbol), theme.qcolor(tint)


def _darken_overlay():
    """Days of the previous and next month: the same cell, slightly darker (not greyed out)."""
    return QtGui.QColor(0, 0, 0, 56) if theme.is_dark() else QtGui.QColor(20, 30, 60, 18)


def _columns(events, length):
    """Side-by-side columns for overlapping blocks: [(start, item, column, columns_in_group)]."""
    placed, group, ends = [], [], []
    for start, item in sorted(events, key=lambda e: e[0]):
        if group and start >= max(ends):  # nothing still running: a new group starts
            placed += [(s, it, c, len(ends)) for s, it, c in group]
            group, ends = [], []
        for col, end in enumerate(ends):
            if end <= start:
                ends[col] = start + length
                break
        else:
            col = len(ends)
            ends.append(start + length)
        group.append((start, item, col))
    placed += [(s, it, c, len(ends)) for s, it, c in group]
    return placed


class CalendarCanvas(QtWidgets.QAbstractScrollArea):
    """Paints the current view and tells the window what was clicked."""
    open_view = QtCore.pyqtSignal(str, object)   # view, date
    create = QtCore.pyqtSignal(object)           # datetime for a new reminder
    edit = QtCore.pyqtSignal(dict)               # reminder to edit

    def __init__(self, get_reminders, parent=None):
        super().__init__(parent)
        self.get_reminders = get_reminders
        self.view, self.date = "month", datetime.date.today()
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setMouseTracking(True)
        self.viewport().setAutoFillBackground(False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self._hits = []      # [(QRectF, kind, payload)] from the last paint, checked in order
        self._hover = None   # hovered date (month, year) or snapped minutes (day)
        self._cache = {}
        self._today = datetime.date.today()
        # The current-time line and "today" move slowly: a check every 30 s is plenty
        self.ticker = QtCore.QTimer(self)
        self.ticker.timeout.connect(self._tick)
        self.ticker.start(30_000)

    # ----- data -----

    def occurrences(self, first, last, specific_only=False):
        """{date: [(datetime, reminder)]} for the days first..last, sorted by time; cached."""
        key = (first, last, specific_only)
        if key not in self._cache:
            days = {}
            for r in self.get_reminders():
                if specific_only and not schedule.is_date_specific(r):
                    continue
                for occ in schedule.occurrences_between(r, first, last):
                    days.setdefault(occ.date(), []).append((occ, r))
            for items in days.values():
                items.sort(key=lambda x: (x[0], x[1].get("text", "")))
            self._cache[key] = days
        return self._cache[key]

    def data_changed(self):
        self._cache.clear()
        self.viewport().update()

    def _tick(self):
        if datetime.date.today() != self._today:
            self._today = datetime.date.today()
            self._cache.clear()
        if self.view == "day" or self._today != self.date:
            self.viewport().update()

    # ----- view -----

    def set_view(self, view, date):
        changed_view = view != self.view or (view == "day" and date != self.date)
        self.view, self.date, self._hover = view, date, None
        self._update_scroll()
        if changed_view:
            sb = self.verticalScrollBar()
            if view == "day":
                now = datetime.datetime.now()
                hour = max(7, now.hour - 3) if date == now.date() else 7
                sb.setValue(round(self._day_top() + hour * self._hour_h()) - theme.px(4))
            else:
                sb.setValue(0)
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scroll()

    def _update_scroll(self):
        vh = self.viewport().height()
        if self.view == "day":
            total = self._day_top() * 2 + 24 * self._hour_h()
        elif self.view == "year":
            total = self._year_layout()["total"]
        else:
            total = vh
        sb = self.verticalScrollBar()
        sb.setRange(0, max(0, round(total - vh)))
        sb.setPageStep(vh)
        sb.setSingleStep(theme.px(24))

    # ----- painting -----

    def paintEvent(self, event):
        p = QtGui.QPainter(self.viewport())
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        self._hits = []
        {"day": self._paint_day, "month": self._paint_month, "year": self._paint_year}[self.view](p)
        p.end()

    def _text(self, p, rect, text, size=13, weight=400, color="text", align=None, elide=True):
        f = theme.font(size, weight)
        p.setFont(f)
        p.setPen(color if isinstance(color, QtGui.QColor) else _col(color))
        if elide:
            text = QtGui.QFontMetrics(f).elidedText(text, QtCore.Qt.TextElideMode.ElideRight, int(rect.width()))
        p.drawText(rect, int(align or (QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)), text)

    # Month: 6 x 7 grid, Monday first; date-specific reminders (one-time, monthly, yearly) listed in the cells

    def _paint_month(self, p):
        px = theme.px
        w, h = self.viewport().width(), self.viewport().height()
        head = px(28)
        first = self.date.replace(day=1)
        start = first - datetime.timedelta(days=first.weekday())
        days = self.occurrences(start, start + datetime.timedelta(days=41), specific_only=True)
        col_w, row_h = w / 7, (h - head) / 6
        for i, name in enumerate(DAY_NAMES):
            self._text(p, QtCore.QRectF(i * col_w + px(8), 0, col_w - px(8), head), name[:3], 12, 500, "muted")
        line_h = px(20)
        for idx in range(42):
            d = start + datetime.timedelta(days=idx)
            row, col = divmod(idx, 7)
            cell = QtCore.QRectF(col * col_w, head + row * row_h, col_w, row_h)
            if d == self._hover:
                p.fillRect(cell, _col("hover"))
            # Date number; today in an accent circle
            num = QtCore.QRectF(cell.x() + px(6), cell.y() + px(5), px(26), px(26))
            if d == self._today:
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.setBrush(_col("accent"))
                p.drawEllipse(num)
                self._text(p, num, str(d.day), 13, 700, "on_accent", QtCore.Qt.AlignmentFlag.AlignCenter, False)
            else:
                self._text(p, num, str(d.day), 13, 600 if d.month == first.month else 400,
                           "text" if d.month == first.month else "text2", QtCore.Qt.AlignmentFlag.AlignCenter, False)
            self._hits.append((num.adjusted(-2, -2, 2, 2), "day", d))
            if d == self._hover:
                plus = QtCore.QRectF(cell.right() - px(28), cell.y() + px(5), px(22), px(26))
                self._text(p, plus, "+", 18, 400, "muted", QtCore.Qt.AlignmentFlag.AlignCenter, False)
            # Reminders that fit; the rest become "+N more"
            items = days.get(d, [])
            top = cell.y() + px(34)
            capacity = max(0, int((cell.bottom() - px(4) - top) // line_h))
            shown = items if len(items) <= capacity else items[:max(0, capacity - 1)]
            for i, (occ, r) in enumerate(shown):
                self._month_item(p, QtCore.QRectF(cell.x() + px(4), top + i * line_h, col_w - px(8), line_h - px(2)),
                                 occ, r, d < self._today)
            if len(shown) < len(items):
                more = QtCore.QRectF(cell.x() + px(8), top + len(shown) * line_h, col_w - px(12), line_h - px(2))
                self._text(p, more, f"+{len(items) - len(shown)} more", 12, 600, "text2")
                self._hits.append((more, "day", d))
            self._hits.append((cell, "new", datetime.datetime.combine(d, NEW_AT)))
            if d.month != first.month:
                p.fillRect(cell, _darken_overlay())
        # Grid lines on top, so darkened cells keep the same lines
        p.setPen(QtGui.QPen(_col("divider"), 1))
        for row in range(7):
            y = round(head + row * row_h) + 0.5
            p.drawLine(QtCore.QPointF(0, y), QtCore.QPointF(w, y))
        for col in range(1, 7):
            x = round(col * col_w) + 0.5
            p.drawLine(QtCore.QPointF(x, head), QtCore.QPointF(x, h))

    def _month_item(self, p, rect, occ, reminder, past):
        px = theme.px
        symbol, tint = _cat_colors(reminder)
        p.save()
        if past:
            p.setOpacity(0.6)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(tint)
        p.drawRoundedRect(rect, px(4), px(4))
        p.setBrush(symbol)
        p.drawRoundedRect(QtCore.QRectF(rect.x() + px(3), rect.y() + px(4), px(3), rect.height() - px(8)), 1.5, 1.5)
        time_rect = QtCore.QRectF(rect.x() + px(10), rect.y(), px(40), rect.height())
        self._text(p, time_rect, f"{occ:%H:%M}", 12, 400, "text2", elide=False)
        fm = QtGui.QFontMetrics(theme.font(12))
        title_x = time_rect.x() + fm.horizontalAdvance("00:00") + px(6)
        self._text(p, QtCore.QRectF(title_x, rect.y(), rect.right() - title_x - px(4), rect.height()),
                   reminder.get("text", ""), 12, 600)
        p.restore()
        self._hits.append((rect, "edit", reminder))

    # Day: a timeline, one hour = 48 px; click a time to add a reminder there

    def _hour_h(self):
        return theme.px(48)

    def _day_top(self):
        return theme.px(12)

    def _gutter(self):
        return theme.px(64)

    def _y_of(self, minutes):
        return self._day_top() + minutes * self._hour_h() / 60 - self.verticalScrollBar().value()

    def _paint_day(self, p):
        px = theme.px
        w = self.viewport().width()
        gutter, hour_h = self._gutter(), self._hour_h()
        right = w - px(16)
        for hour in range(25):
            y = round(self._y_of(hour * 60)) + 0.5
            p.setPen(QtGui.QPen(_col("divider"), 1))
            p.drawLine(QtCore.QPointF(gutter, y), QtCore.QPointF(right, y))
            if hour < 24:
                half = round(self._y_of(hour * 60 + 30)) + 0.5
                p.setPen(QtGui.QPen(_col("divider", 0.05 if theme.is_dark() else 0.06), 1))
                p.drawLine(QtCore.QPointF(gutter, half), QtCore.QPointF(right, half))
                self._text(p, QtCore.QRectF(0, y - px(9), gutter - px(12), px(18)), f"{hour:02d}:00", 12, 400,
                           "muted", QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter, False)

        now = datetime.datetime.now()
        items = self.occurrences(self.date, self.date).get(self.date, [])
        x0, block_h = gutter + px(8), hour_h / 2 - px(2)
        width = right - x0
        events = [(occ.hour * 60 + occ.minute, (occ, r)) for occ, r in items]
        for start, (occ, r), col, cols in _columns(events, 30):
            col_w = width / cols
            rect = QtCore.QRectF(x0 + col * col_w, self._y_of(start) + 1, col_w - px(4), block_h)
            self._day_block(p, rect, r, occ < now)

        if self._hover is not None:
            m = self._hover
            ghost = QtCore.QRectF(x0, self._y_of(m) + 1, width - px(4), block_h)
            p.setPen(QtGui.QPen(_col("accent", 0.7), 1, QtCore.Qt.PenStyle.DashLine))
            p.setBrush(_col("accent", 0.12))
            p.drawRoundedRect(ghost, px(6), px(6))
            self._text(p, ghost.adjusted(px(10), 0, -px(8), 0), f"{m // 60:02d}:{m % 60:02d}   New reminder",
                       13, 600, "accent")

        if self.date == now.date():
            y = self._y_of(now.hour * 60 + now.minute)
            p.setPen(QtGui.QPen(_col("accent"), 2))
            p.drawLine(QtCore.QPointF(gutter, y), QtCore.QPointF(right, y))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(_col("accent"))
            p.drawEllipse(QtCore.QPointF(gutter, y), px(4), px(4))

    def _day_block(self, p, rect, reminder, past):
        px = theme.px
        symbol, tint = _cat_colors(reminder)
        p.save()
        if past:
            p.setOpacity(0.55)
        p.setPen(QtGui.QPen(QtGui.QColor(symbol.red(), symbol.green(), symbol.blue(), 64), 1))
        p.setBrush(_col("surface_solid"))
        p.drawRoundedRect(rect, px(6), px(6))
        p.setBrush(tint)
        p.drawRoundedRect(rect, px(6), px(6))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(symbol)
        p.drawRoundedRect(QtCore.QRectF(rect.x() + px(4), rect.y() + px(5), px(3), rect.height() - px(10)), 1.5, 1.5)
        x = rect.x() + px(14)
        cat = schedule.category_of(reminder)
        if cat != "none":
            size = px(16)
            p.drawPixmap(QtCore.QPointF(x, rect.center().y() - size / 2), theme.pixmap(f"cat-{cat}", symbol.name(), size))
            x += size + px(8)
        title = reminder.get("text", "")
        f = theme.font(13, 600)
        title_w = min(QtGui.QFontMetrics(f).horizontalAdvance(title), rect.right() - x - px(8))
        self._text(p, QtCore.QRectF(x, rect.y(), title_w, rect.height()), title, 13, 600)
        rule_x = x + title_w + px(10)
        if rect.right() - rule_x > px(40):
            self._text(p, QtCore.QRectF(rule_x, rect.y(), rect.right() - rule_x - px(8), rect.height()),
                       schedule.describe_rule(reminder), 12, 400, "text2")
        p.restore()
        self._hits.append((rect, "edit", reminder))

    def _minutes_at(self, y):
        minutes = (y + self.verticalScrollBar().value() - self._day_top()) * 60 / self._hour_h()
        return int(min(max(minutes // 15 * 15, 0), 23 * 60 + 45))

    # Year: 12 small months; dots on days with date-specific reminders (birthdays, bills)

    def _year_layout(self):
        px = theme.px
        w, vh = self.viewport().width(), self.viewport().height()
        cols = 4 if w > px(880) else 3
        rows = 12 // cols
        gap_x, gap_y, margin = px(28), px(18), px(4)
        mini_w = (w - 2 * margin - gap_x * (cols - 1)) / cols
        head_h, week_h = px(28), px(22)
        fit = (vh - 2 * margin - gap_y * (rows - 1)) / rows
        row_h = min(max((fit - head_h - week_h) / 6, px(22)), px(34))
        mini_h = head_h + week_h + 6 * row_h
        return {"cols": cols, "gap_x": gap_x, "gap_y": gap_y, "margin": margin, "mini_w": mini_w,
                "head_h": head_h, "week_h": week_h, "row_h": row_h, "mini_h": mini_h,
                "total": 2 * margin + rows * mini_h + (rows - 1) * gap_y}

    def _paint_year(self, p):
        px = theme.px
        L = self._year_layout()
        year = self.date.year
        days = self.occurrences(datetime.date(year, 1, 1), datetime.date(year, 12, 31), specific_only=True)
        off = self.verticalScrollBar().value()
        cell_w = L["mini_w"] / 7
        for m in range(1, 13):
            row, col = divmod(m - 1, L["cols"])
            x = L["margin"] + col * (L["mini_w"] + L["gap_x"])
            y = L["margin"] + row * (L["mini_h"] + L["gap_y"]) - off
            if y > self.viewport().height() or y + L["mini_h"] < 0:
                continue
            current = (year, m) == (self._today.year, self._today.month)
            head = QtCore.QRectF(x + px(4), y, L["mini_w"] - px(4), L["head_h"])
            self._text(p, head, MONTH_NAMES[m - 1], 15, 650, "accent" if current else "text")
            fm = QtGui.QFontMetrics(theme.font(15, 650))
            self._hits.append((QtCore.QRectF(head.x(), head.y(), fm.horizontalAdvance(MONTH_NAMES[m - 1]) + px(8),
                                             head.height()), "month", datetime.date(year, m, 1)))
            for i, name in enumerate(DAY_NAMES):
                self._text(p, QtCore.QRectF(x + i * cell_w, y + L["head_h"], cell_w, L["week_h"]), name[0], 12, 500,
                           "muted", QtCore.Qt.AlignmentFlag.AlignCenter, False)
            first_wd = datetime.date(year, m, 1).weekday()
            for day in range(1, calendar.monthrange(year, m)[1] + 1):
                d = datetime.date(year, m, day)
                r, c = divmod(first_wd + day - 1, 7)
                cell = QtCore.QRectF(x + c * cell_w, y + L["head_h"] + L["week_h"] + r * L["row_h"], cell_w, L["row_h"])
                # Number sits a little above center, leaving room for the dot under it
                num = cell.adjusted(0, 0, 0, -px(5))
                side = min(cell_w, L["row_h"]) - px(4)
                circle = QtCore.QRectF(num.center().x() - side / 2, num.center().y() - side / 2, side, side)
                if d == self._today or d == self._hover:
                    p.setPen(QtCore.Qt.PenStyle.NoPen)
                    p.setBrush(_col("accent") if d == self._today else _col("hover", 0.14 if theme.is_dark() else 0.12))
                    p.drawEllipse(circle)
                today = d == self._today
                self._text(p, num, str(day), 12, 700 if today else 400, "on_accent" if today else "text",
                           QtCore.Qt.AlignmentFlag.AlignCenter, False)
                items = days.get(d)
                if items:
                    p.setPen(QtCore.Qt.PenStyle.NoPen)
                    p.setBrush(_cat_colors(items[0][1])[0])
                    p.drawEllipse(QtCore.QPointF(cell.center().x(), max(circle.bottom(), num.bottom() - px(2)) + px(3)),
                                  px(2.5), px(2.5))
                self._hits.append((cell, "day", d))

    def _year_tooltip(self, d):
        year = self.date.year
        items = self.occurrences(datetime.date(year, 1, 1), datetime.date(year, 12, 31), specific_only=True).get(d, [])
        return "\n".join(f"{occ:%H:%M}  {r.get('text', '')}" for occ, r in items)

    # ----- mouse -----

    def _hit_at(self, pos):
        for rect, kind, payload in self._hits:
            if rect.contains(pos):
                return kind, payload
        return None, None

    def mouseMoveEvent(self, event):
        pos = event.position()
        kind, payload = self._hit_at(pos)
        if self.view == "day":
            hover = self._minutes_at(pos.y()) if kind is None and pos.x() >= self._gutter() else None
        elif self.view == "month":
            hover = payload.date() if kind == "new" else payload if kind == "day" else (
                self._hover if kind == "edit" else None)
        else:
            hover = payload if kind == "day" else None
            tip = self._year_tooltip(hover) if hover else ""
            if tip:
                QtWidgets.QToolTip.showText(event.globalPosition().toPoint(), tip, self.viewport())
            else:
                QtWidgets.QToolTip.hideText()
        clickable = kind is not None or hover is not None
        self.viewport().setCursor(QtCore.Qt.CursorShape.PointingHandCursor if clickable
                                  else QtCore.Qt.CursorShape.ArrowCursor)
        if hover != self._hover:
            self._hover = hover
            self.viewport().update()

    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.Type.Leave and self._hover is not None:
            self._hover = None
            QtWidgets.QToolTip.hideText()
            self.viewport().update()
        return super().viewportEvent(event)

    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.view == "day":
            self._hover = None  # the ghost would sit at a stale time until the mouse moves

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        kind, payload = self._hit_at(pos)
        QtWidgets.QToolTip.hideText()
        if kind == "edit":
            self.edit.emit(payload)
        elif kind == "new":
            self.create.emit(payload)
        elif kind in ("day", "month"):
            self.open_view.emit(kind, payload)
        elif self.view == "day" and pos.x() >= self._gutter():
            m = self._minutes_at(pos.y())
            self.create.emit(datetime.datetime.combine(self.date, datetime.time(m // 60, m % 60)))


class CalendarWindow(QtWidgets.QWidget):
    """Toolbar (Today, arrows, period, Day/Month/Year, New reminder) over the painted canvas."""

    def __init__(self, app):
        super().__init__(None, QtCore.Qt.WindowType.Window)
        self.app = app
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Notify calendar")
        px = theme.px
        self.setMinimumSize(px(720), px(520))
        area = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(px(980), area.width() - 40), min(px(700), area.height() - 40))
        self.move(area.center() - self.rect().center())

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(px(20), px(16), px(20), px(14))
        root.setSpacing(px(8))
        bar = QtWidgets.QHBoxLayout()
        bar.setSpacing(px(6))
        today = QtWidgets.QPushButton("Today")
        today.setToolTip("Go to today (T)")
        today.clicked.connect(self.go_today)
        bar.addWidget(today)
        bar.addSpacing(px(4))
        self.prev = IconButton("chevron-down", "Previous (Left arrow)", 36, 20)
        self.prev.clicked.connect(lambda: self.step(-1))
        self.next = IconButton("chevron-down", "Next (Right arrow)", 36, 20)
        self.next.clicked.connect(lambda: self.step(1))
        bar.addWidget(self.prev)
        bar.addWidget(self.next)
        bar.addSpacing(px(8))
        self.title = label("", "h2")
        bar.addWidget(self.title)
        bar.addStretch()
        self.views = Segmented(["Day", "Month", "Year"])
        self.views.setFixedWidth(px(240))
        self.views.changed.connect(lambda i: self.set_view(VIEWS[i]))
        bar.addWidget(self.views)
        bar.addSpacing(px(8))
        new = QtWidgets.QPushButton(" New reminder")
        new.setProperty("kind", "primary")
        new.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        new.clicked.connect(self._new_for_view)
        self.new = new
        bar.addWidget(new)
        root.addLayout(bar)

        self.hint = label("", "meta")
        root.addWidget(self.hint)
        self.canvas = CalendarCanvas(app.data_manager.get_reminders)
        self.canvas.open_view.connect(lambda view, d: self.set_view(view, d))
        self.canvas.create.connect(self._create)
        self.canvas.edit.connect(self._edit)
        root.addWidget(self.canvas, 1)

        for key, action in (("Left", lambda: self.step(-1)), ("Right", lambda: self.step(1)),
                            ("T", self.go_today), ("D", lambda: self.set_view("day")),
                            ("M", lambda: self.set_view("month")), ("Y", lambda: self.set_view("year")),
                            ("Esc", self.close)):
            QtGui.QShortcut(QtGui.QKeySequence(key), self, action)

        self.view, self.date = "month", datetime.date.today()
        self.restyle()
        self._sync()
        self.canvas.setFocus()

    # ----- look -----

    def restyle(self):
        """Colors that aren't in the stylesheet (icons, title bar); called again on theme change."""
        px = theme.px
        down = theme.pixmap("chevron-down", theme.c("text2"), px(20))
        for button, angle in ((self.prev, 90), (self.next, -90)):
            pm = down.transformed(QtGui.QTransform().rotate(angle), QtCore.Qt.TransformationMode.SmoothTransformation)
            pm.setDevicePixelRatio(down.devicePixelRatio())
            button.setIcon(QtGui.QIcon(pm))
        self.new.setIcon(theme.icon("add", theme.c("on_accent"), px(18)))
        self.new.setIconSize(QtCore.QSize(px(18), px(18)))
        if self.isVisible():
            theme.style_title_bar(self)
        self.canvas.data_changed()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        theme.style_title_bar(self)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), _col("surface_solid"))
        p.end()

    # ----- navigation -----

    def _sync(self):
        d = self.date
        if self.view == "day":
            text = f"{DAY_NAMES[d.weekday()]}, {MONTH_NAMES[d.month - 1]} {d.day}"
            if d.year != datetime.date.today().year:
                text += f", {d.year}"
        elif self.view == "month":
            text = f"{MONTH_NAMES[d.month - 1]} {d.year}"
        else:
            text = str(d.year)
        self.title.setText(text)
        self.hint.setText(HINTS[self.view])
        # set_index reports a change, which would call set_view again
        self.views.blockSignals(True)
        self.views.set_index(VIEWS.index(self.view))
        self.views.blockSignals(False)
        self.canvas.set_view(self.view, d)

    def set_view(self, view, date=None):
        self.view = view
        if date is not None:
            self.date = date
        self._sync()

    def step(self, n):
        if self.view == "day":
            self.date += datetime.timedelta(days=n)
        else:
            self.date = shift_month(self.date, n if self.view == "month" else 12 * n)
        self._sync()

    def go_today(self):
        self.date = datetime.date.today()
        self._sync()

    # ----- reminders -----

    def _new_for_view(self):
        """New reminder from the toolbar: on the shown day in Day view, otherwise 5 minutes from now."""
        if self.view == "day" and self.date != datetime.date.today():
            self._create(datetime.datetime.combine(self.date, NEW_AT))
        else:
            self.app.open_editor(None, parent=self)

    def _create(self, when):
        self.app.open_editor(None, initial=when, parent=self)

    def _edit(self, reminder):
        self.app.open_editor(reminder, parent=self)

    def refresh(self):
        self.canvas.data_changed()
