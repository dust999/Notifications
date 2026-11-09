"""Calendar window: Day, Month and Year views of all reminders. Click a day or a time to add one.

Each view is painted by one widget (CalendarCanvas) with its own hit-testing: no widget per day
or per reminder, so the window stays light. It is created when opened and destroyed when closed.
Layout follows design/calendar.html (approved mockup) and design/CALENDAR-NOTES.md.
"""
import calendar
import datetime
import time

from PyQt6 import QtCore, QtGui, QtWidgets

import schedule
import theme
from widgets import IconButton, Segmented, label, paint_surface

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
    """(symbol color, fill) for a reminder: its own color if the user chose one, else its category's."""
    own = theme.reminder_color(reminder.get("color"))
    if own is not None:
        fill = QtGui.QColor(own)
        fill.setAlphaF(0.24 if theme.is_dark() else 0.17)
        return own, fill
    symbol, tint = theme.c("cat")[schedule.category_of(reminder)]
    return theme.qcolor(symbol), theme.qcolor(tint)


def _day_colors(items):
    """Colors for a day's bar in Year view: one per chosen color present (always in the same
    order: red, yellow, green, ...), plus one grey part if some reminders have no color."""
    chosen = {r.get("color") for _occ, r in items if theme.reminder_color(r.get("color")) is not None}
    colors = [theme.reminder_color(key) for key, *_ in theme.REMINDER_COLORS if key in chosen]
    if any(theme.reminder_color(r.get("color")) is None for _occ, r in items):
        colors.append(_col("muted"))
    return colors


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
    show_day = QtCore.pyqtSignal(object, QtCore.QRect)  # date, its cell on screen: open the day's card

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
        self._ignore_until = 0.0  # see ignore_click
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
            elif view == "year":
                # The whole year may not fit: make sure the shown month (today's, from Today) is visible
                L = self._year_layout()
                row = (date.month - 1) // L["cols"]
                top = L["margin"] + row * (L["mini_h"] + L["gap_y"])
                bottom = top + L["mini_h"]
                vh = self.viewport().height()
                sb.setValue(0 if bottom <= vh else round(min(top, bottom - vh + L["margin"])))
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
        start = schedule.week_start_of(first)
        days = self.occurrences(start, start + datetime.timedelta(days=41), specific_only=True)
        col_w, row_h = w / 7, (h - head) / 6
        for i, wd in enumerate(schedule.week_order()):
            self._text(p, QtCore.QRectF(i * col_w + px(8), 0, col_w - px(8), head), DAY_NAMES[wd][:3], 12, 500, "muted")
        line_h = px(20)
        for idx in range(42):
            d = start + datetime.timedelta(days=idx)
            row, col = divmod(idx, 7)
            cell = QtCore.QRectF(col * col_w, head + row * row_h, col_w, row_h)
            if d == self._hover or (d, "more") == self._hover:
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
                text = f"+{len(items) - len(shown)} more"
                text_w = QtGui.QFontMetrics(theme.font(12, 600)).horizontalAdvance(text)
                more = QtCore.QRectF(cell.x() + px(4), top + len(shown) * line_h, text_w + px(16), line_h - px(2))
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.setBrush(_col("accent", 0.22 if (d, "more") == self._hover else 0.12))
                p.drawRoundedRect(more, px(4), px(4))
                self._text(p, more, text, 12, 600, "accent", QtCore.Qt.AlignmentFlag.AlignCenter, False)
                self._hits.append((more, "more", (d, cell)))
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
        colored = theme.reminder_color(reminder.get("color")) is not None
        self._text(p, time_rect, f"{occ:%H:%M}", 12, 600 if colored else 400, symbol if colored else "text2",
                   elide=False)
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
        # +2: elidedText gets a whole-pixel width, which can cut a title that exactly fits
        title_w = min(QtGui.QFontMetrics(f).horizontalAdvance(title) + 2, rect.right() - x - px(8))
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
        """Compact: the whole year fits without scrolling (design/year-variants.html, variant B)."""
        px = theme.px
        w, vh = self.viewport().width(), self.viewport().height()
        cols = 4 if w > px(880) else 3
        rows = 12 // cols
        gap_x, gap_y, margin = px(24), px(10), px(4)
        mini_w = (w - 2 * margin - gap_x * (cols - 1)) / cols
        head_h, week_h = px(24), px(18)
        fit = (vh - 2 * margin - gap_y * (rows - 1)) / rows
        row_h = min(max((fit - head_h - week_h) / 6, px(20)), px(26))
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
        dark = theme.is_dark()
        accent = _col("accent")
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
            for i, wd in enumerate(schedule.week_order()):
                self._text(p, QtCore.QRectF(x + i * cell_w, y + L["head_h"], cell_w, L["week_h"]), DAY_NAMES[wd][0], 12, 500,
                           "muted", QtCore.Qt.AlignmentFlag.AlignCenter, False)
            first_wd = schedule.column_of(datetime.date(year, m, 1))
            for day in range(1, calendar.monthrange(year, m)[1] + 1):
                d = datetime.date(year, m, day)
                r, c = divmod(first_wd + day - 1, 7)
                cell = QtCore.QRectF(x + c * cell_w, y + L["head_h"] + L["week_h"] + r * L["row_h"], cell_w, L["row_h"])
                # One pill per day holds the number and its color line: hover and today outline both
                pw = min(cell_w - px(4), px(28))
                pill = QtCore.QRectF(cell.center().x() - pw / 2, cell.y() + px(0.5), pw, cell.height() - px(1))
                num = QtCore.QRectF(pill.x(), pill.y(), pill.width(), pill.height() - px(7))
                today, hovered = d == self._today, d == self._hover
                if today or hovered:
                    if today:
                        fill = QtGui.QColor(accent)
                        fill.setAlphaF((0.13 if dark else 0.09) + (0.06 if hovered else 0))
                        pen = QtGui.QPen(accent, 1)
                    else:
                        fill = _col("hover", 0.10) if dark else QtGui.QColor(47, 95, 207, 18)
                        pen = QtGui.QPen(QtGui.QColor(214, 226, 255, 51) if dark else QtGui.QColor(47, 95, 207, 77), 1)
                    p.setPen(pen)
                    p.setBrush(fill)
                    p.drawRoundedRect(pill.adjusted(0.5, 0.5, -0.5, -0.5), px(7), px(7))
                self._text(p, num, str(day), 12, 700 if today else 400, "accent" if today else "text",
                           QtCore.Qt.AlignmentFlag.AlignCenter, False)
                items = days.get(d)
                if items:
                    # Thin line right under the number, split by color: payday green + a red bill
                    # on one day show as half green, half red
                    colors = _day_colors(items)
                    gap = px(1.5) if len(colors) > 1 else 0
                    bar_w = min(px(14) + px(4) * (len(colors) - 1), pill.width() - px(6))
                    part = (bar_w - gap * (len(colors) - 1)) / len(colors)
                    x0, y0 = pill.center().x() - bar_w / 2, num.bottom() + px(0.5)
                    p.setPen(QtCore.Qt.PenStyle.NoPen)
                    for i, color in enumerate(colors):
                        p.setBrush(color)
                        p.drawRoundedRect(QtCore.QRectF(x0 + i * (part + gap), y0, part, px(2)), 1, 1)
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
                (payload[0], "more") if kind == "more" else self._hover if kind == "edit" else None)
            # Titles in the cells get cut short: the full one on hover
            if kind == "edit":
                QtWidgets.QToolTip.showText(event.globalPosition().toPoint(),
                                            payload.get("text", "") + "\n" + schedule.describe_rule(payload),
                                            self.viewport())
            else:
                QtWidgets.QToolTip.hideText()
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

    def ignore_click(self):
        """A popup over the calendar just closed: the click that closed it must not also act here
        (e.g. open "New reminder" on the day under the mouse). A real second click still works."""
        self._ignore_until = time.monotonic() + 0.25

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.MouseButton.LeftButton or time.monotonic() < self._ignore_until:
            return
        pos = event.position()
        kind, payload = self._hit_at(pos)
        QtWidgets.QToolTip.hideText()
        # Windows (editor, day card) open once this click is over, not in the middle of it,
        # so the press and release both land here before a new window takes the focus.
        later = lambda fn: QtCore.QTimer.singleShot(0, fn)
        if kind == "edit":
            later(lambda: self.edit.emit(payload))
        elif kind == "new":
            later(lambda: self.create.emit(payload))
        elif kind in ("day", "month"):
            self.open_view.emit(kind, payload)
        elif kind == "more":
            d, cell = payload
            rect = QtCore.QRect(self.viewport().mapToGlobal(cell.topLeft().toPoint()), cell.size().toSize())
            later(lambda: self.show_day.emit(d, rect))
        elif self.view == "day" and pos.x() >= self._gutter():
            m = self._minutes_at(pos.y())
            when = datetime.datetime.combine(self.date, datetime.time(m // 60, m % 60))
            later(lambda: self.create.emit(when))


class _DayRows(QtWidgets.QWidget):
    """Painted rows for DayCard: color mark, time, full title and the repeat rule under it."""
    clicked = QtCore.pyqtSignal(dict)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items   # [(datetime, reminder)]
        self.hover = None
        self.row_h = theme.px(48)
        self.setMouseTracking(True)
        self.setFixedHeight(self.row_h * len(items))

    def paintEvent(self, event):
        px = theme.px
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        now = datetime.datetime.now()
        for i, (occ, r) in enumerate(self.items):
            rect = QtCore.QRectF(0, i * self.row_h, self.width(), self.row_h - px(2))
            symbol, tint = _cat_colors(r)
            p.save()
            if occ < now:
                p.setOpacity(0.6)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(_col("hover") if i == self.hover else tint)
            p.drawRoundedRect(rect, px(6), px(6))
            p.setBrush(symbol)
            p.drawRoundedRect(QtCore.QRectF(rect.x() + px(5), rect.y() + px(8), px(3), rect.height() - px(16)), 1.5, 1.5)
            colored = theme.reminder_color(r.get("color")) is not None
            p.setFont(theme.font(13, 600))
            p.setPen(symbol if colored else _col("text2"))
            time_rect = QtCore.QRectF(rect.x() + px(16), rect.y() + px(5), px(48), px(20))
            p.drawText(time_rect, int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
                       f"{occ:%H:%M}")
            x = time_rect.x() + px(52)
            fm = QtGui.QFontMetrics(theme.font(13, 600))
            p.setPen(_col("text"))
            p.drawText(QtCore.QRectF(x, rect.y() + px(5), rect.right() - x - px(8), px(20)),
                       int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
                       fm.elidedText(r.get("text", ""), QtCore.Qt.TextElideMode.ElideRight, int(rect.right() - x - px(8))))
            p.setFont(theme.font(12))
            p.setPen(_col("text2"))
            p.drawText(QtCore.QRectF(x, rect.y() + px(24), rect.right() - x - px(8), px(18)),
                       int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
                       schedule.describe_rule(r))
            p.restore()
        p.end()

    def _row_at(self, pos):
        i = int(pos.y() // self.row_h)
        return i if 0 <= i < len(self.items) else None

    def mouseMoveEvent(self, event):
        i = self._row_at(event.position())
        if i != self.hover:
            self.hover = i
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor if i is not None else QtCore.Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def mousePressEvent(self, event):
        i = self._row_at(event.position())
        if i is not None and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.items[i][1])


class DayCard(QtWidgets.QFrame):
    """All reminders of one day, over its Month cell: dated ones (birthdays, bills) first,
    then the daily and weekly ones. Click one to edit it; closes on any click outside."""
    edit = QtCore.pyqtSignal(dict)
    open_day = QtCore.pyqtSignal(object)
    create = QtCore.pyqtSignal(object)
    closed = QtCore.pyqtSignal()

    def __init__(self, date, items, parent=None):
        super().__init__(parent, QtCore.Qt.WindowType.Popup | QtCore.Qt.WindowType.FramelessWindowHint
                         | QtCore.Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        # A click outside only closes the popup; it isn't passed on to what's underneath
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoMouseReplay)
        px = theme.px
        self.date = date
        self.setFixedWidth(px(340))
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(px(14), px(12), px(14), px(14))
        root.setSpacing(px(6))
        head = QtWidgets.QHBoxLayout()
        head.addWidget(label(f"{DAY_NAMES[date.weekday()]}, {MONTH_NAMES[date.month - 1]} {date.day}", "row"))
        head.addStretch()
        close = IconButton("close", "Close", 28, 16)
        close.clicked.connect(self.close)
        head.addWidget(close)
        root.addLayout(head)

        body = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(px(4))
        dated = [(o, r) for o, r in items if schedule.is_date_specific(r)]
        repeating = [(o, r) for o, r in items if not schedule.is_date_specific(r)]
        for title, group in (("On this date", dated), ("Repeating", repeating)):
            if not group:
                continue
            lay.addWidget(label(title, "section"))
            rows = _DayRows(group)
            rows.clicked.connect(self._edit)
            lay.addWidget(rows)
            lay.addSpacing(px(4))
        if not items:
            lay.addWidget(label("Nothing planned", "meta"))
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        body.adjustSize()
        scroll.setFixedHeight(min(body.sizeHint().height(), px(420)))
        root.addWidget(scroll)

        buttons = QtWidgets.QHBoxLayout()
        open_day = QtWidgets.QPushButton("Open day")
        open_day.clicked.connect(lambda: (self.close(), self.open_day.emit(self.date)))
        new = QtWidgets.QPushButton("New reminder")
        new.setProperty("kind", "primary")
        new.clicked.connect(lambda: (self.close(), self.create.emit(datetime.datetime.combine(self.date, NEW_AT))))
        buttons.addWidget(open_day)
        buttons.addStretch()
        buttons.addWidget(new)
        root.addSpacing(px(4))
        root.addLayout(buttons)

    def _edit(self, reminder):
        self.edit.emit(reminder)  # the window opens the editor after this click (see _show_day_card)
        self.close()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def paintEvent(self, event):
        paint_surface(self, False, theme.px(10), "popup")

    def show_at(self, cell):
        """Over the clicked cell, like Google Calendar's day card; kept on the screen."""
        self.adjustSize()
        area = QtGui.QGuiApplication.screenAt(cell.center()).availableGeometry() \
            if QtGui.QGuiApplication.screenAt(cell.center()) else QtGui.QGuiApplication.primaryScreen().availableGeometry()
        x = min(max(cell.left() - theme.px(4), area.left() + 8), area.right() - self.width() - 8)
        y = min(max(cell.top() - theme.px(4), area.top() + 8), area.bottom() - self.height() - 8)
        self.move(x, y)
        self.show()


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
        self.canvas.show_day.connect(self._show_day_card)
        root.addWidget(self.canvas, 1)

        for key, action in (("Left", lambda: self.step(-1)), ("Right", lambda: self.step(1)),
                            ("T", self.go_today), ("D", lambda: self.set_view("day")),
                            ("M", lambda: self.set_view("month")), ("Y", lambda: self.set_view("year")),
                            ("Esc", self.close)):
            QtGui.QShortcut(QtGui.QKeySequence(key), self, action)

        self.view, self.date = "month", datetime.date.today()
        self.editor = None  # the reminder editor opened from here, while it's open
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
            self._open_editor()

    def _show_day_card(self, date, cell):
        """Everything on one day in a card over its cell (from "+N more" in Month view)."""
        items = self.canvas.occurrences(date, date).get(date, [])
        card = DayCard(date, items, self)
        # The card is deleted when it closes: open the editor from here, once the click is over
        card.edit.connect(lambda r: QtCore.QTimer.singleShot(0, lambda: self._edit(r)))
        card.open_day.connect(lambda d: self.set_view("day", d))
        card.create.connect(lambda when: QtCore.QTimer.singleShot(0, lambda: self._create(when)))
        card.closed.connect(self.canvas.ignore_click)
        card.show_at(cell)

    def _create(self, when):
        self._open_editor(initial=when)

    def _edit(self, reminder):
        self._open_editor(reminder)

    def _open_editor(self, reminder=None, initial=None):
        """The editor stays clickable-around: a click anywhere on the calendar closes it unsaved
        (like Google Calendar), and that click does nothing else."""
        if self.editor is not None:
            self.editor.reject()
        editor = self.app.open_editor(reminder, initial=initial, parent=self, modal=False)
        self.editor = editor
        editor.finished.connect(lambda _=None, e=editor: self._editor_closed(e))
        QtWidgets.QApplication.instance().installEventFilter(self)

    def _editor_closed(self, editor):
        if self.editor is editor:
            self.editor = None
            QtWidgets.QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if (self.editor is not None and event.type() == QtCore.QEvent.Type.MouseButtonPress
                and isinstance(obj, QtWidgets.QWidget) and obj.window() is self):
            self.editor.reject()
            self.canvas.ignore_click()
            return True
        return False

    def closeEvent(self, event):
        if self.editor is not None:
            self.editor.reject()
        super().closeEvent(event)

    def refresh(self):
        self.canvas.data_changed()
