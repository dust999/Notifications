"""The main window: a Windows 11 style flyout above the tray icon.

Created when opened and destroyed when closed, so it costs no memory while hidden.
"""
import datetime

from PyQt6 import QtCore, QtWidgets

import schedule
import theme
from widgets import CategoryBadge, ElidedLabel, GlassWindow, IconButton, NextUpGlow, confirm, divider, label

GROUPS = ["Today", "Tomorrow", "This week", "Later"]


class ReminderRow(QtWidgets.QWidget):
    def __init__(self, reminder, meta, right, on_edit=None, on_delete=None, done=False):
        super().__init__()
        self.setObjectName("row")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground)
        self.setFixedHeight(theme.px(62))
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 10, 6)
        lay.setSpacing(theme.px(12))
        badge = CategoryBadge(schedule.category_of(reminder))
        badge.dimmed = done
        lay.addWidget(badge)

        text = QtWidgets.QVBoxLayout()
        text.setSpacing(1)
        # Elided labels shrink to the row's width, so long titles never push the row under the scrollbar
        title = ElidedLabel(reminder.get("text", ""), "row")
        meta_lbl = ElidedLabel(meta, "meta")
        if done:
            title.setStyleSheet(f"color: {theme.c('muted')};")
        text.addWidget(title)
        text.addWidget(meta_lbl)
        lay.addLayout(text, 1)

        self.right = label(right, "meta")
        lay.addWidget(self.right)
        self.actions = []
        if on_edit:
            edit = IconButton("edit", "Edit reminder", 32, 18)
            edit.clicked.connect(lambda: on_edit(reminder))
            delete = IconButton("delete", "Delete reminder", 32, 18)
            delete.clicked.connect(lambda: on_delete(reminder))
            for b in (edit, delete):
                b.hide()
                lay.addWidget(b)
                self.actions.append(b)

    def _show_actions(self, show):
        if self.actions:
            self.right.setVisible(not show)
            for b in self.actions:
                b.setVisible(show)

    def enterEvent(self, event):
        self._show_actions(True)

    def leaveEvent(self, event):
        if not any(b.hasFocus() for b in self.actions):
            self._show_actions(False)


class RemindersFlyout(GlassWindow):
    def __init__(self, app):
        super().__init__(flags=QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
                         | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.app = app
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        screen_h = QtWidgets.QApplication.primaryScreen().availableGeometry().height()
        self.setFixedSize(theme.px(450), min(theme.px(680), screen_h - 40))
        self.setWindowTitle("Notify")
        self.tab = 0

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 10)
        root.setSpacing(0)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(theme.px(10))
        mark = QtWidgets.QLabel()
        mark.setPixmap(theme.pixmap("tray", theme.c("accent"), theme.px(28)))
        head.addWidget(mark)
        head.addWidget(label("Notify", "h1"))
        head.addStretch()
        new = QtWidgets.QPushButton(" New reminder")
        new.setProperty("kind", "primary")
        new.setIcon(theme.icon("add", theme.c("on_accent"), theme.px(18)))
        new.setIconSize(QtCore.QSize(theme.px(18), theme.px(18)))
        new.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        new.clicked.connect(lambda: self.app.open_editor(None))
        head.addWidget(new)
        # Settings sits next to "New reminder": a square as tall as that button
        settings = IconButton("settings", "Settings", 36, 20)
        settings.setProperty("kind", "tool")
        side = new.sizeHint().height()
        settings._side = side
        settings.setFixedSize(side, side)
        settings.clicked.connect(self.app.show_settings_dialog)
        calendar = IconButton("calendar", "Calendar", 36, 20)
        calendar.setProperty("kind", "tool")
        calendar._side = side
        calendar.setFixedSize(side, side)
        calendar.clicked.connect(lambda: self.app.show_calendar())
        head.addWidget(calendar)
        head.addWidget(settings)
        root.addSpacing(4)
        root.addLayout(head)
        root.addSpacing(14)

        self.next_box = NextUpGlow()
        nb = QtWidgets.QVBoxLayout(self.next_box)
        nb.setContentsMargins(0, 8, 0, 10)
        nb.setSpacing(4)
        nb.addWidget(label("Next up", "caption"))
        self.next_title = ElidedLabel("", "next")
        nb.addWidget(self.next_title)
        line = QtWidgets.QHBoxLayout()
        line.setSpacing(6)
        clock = QtWidgets.QLabel()
        clock.setPixmap(theme.pixmap("clock", theme.c("accent"), theme.px(16)))
        line.addWidget(clock)
        self.next_count = label("", "accent")
        line.addWidget(self.next_count)
        line.addSpacing(theme.px(12))
        self.next_when = ElidedLabel("", "meta")
        self.next_when.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        line.addWidget(self.next_when, 1)
        nb.addLayout(line)
        root.addWidget(self.next_box)
        root.addSpacing(10)

        tabs = QtWidgets.QHBoxLayout()
        tabs.setSpacing(theme.px(22))
        self.tab_group = QtWidgets.QButtonGroup(self)
        self.counts = []
        for i, name in enumerate(("Upcoming", "Done today")):
            box = QtWidgets.QHBoxLayout()
            box.setSpacing(theme.px(8))
            b = QtWidgets.QPushButton(name)
            b.setProperty("kind", "tab")
            b.setCheckable(True)
            b.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.tab_group.addButton(b, i)
            count = label("0", "count")
            self.counts.append(count)
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            box.addWidget(b)
            # Small pill centered on the tab text, not stretched to the tab's full height
            box.addWidget(count, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
            tabs.addLayout(box)
        tabs.addStretch()
        self.tab_group.button(0).setChecked(True)
        self.tab_group.idClicked.connect(self._switch_tab)
        root.addLayout(tabs)
        root.addWidget(divider())
        root.addSpacing(theme.px(4))

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # The list runs to the bottom of the window; no footer
        root.addWidget(self.scroll, 1)

        # Countdown text only changes once a minute; refresh while open
        self.ticker = QtCore.QTimer(self)
        self.ticker.timeout.connect(self.refresh)
        self.ticker.start(30_000)
        self.refresh()
        self.setFocus()  # no button gets a focus frame on open

    # ----- data -----

    def _entries(self, now):
        reminders = self.app.data_manager.get_reminders()
        completed = {c["id"]: c.get("completed_at") for c in self.app.data_manager.get_completed()}
        upcoming, done = [], []
        for r in reminders:
            last = completed.get(r.get("id"))
            occ = schedule.next_occurrence(r, now, last)
            if occ is not None:
                upcoming.append((occ, r))
            if last:
                try:
                    shown = datetime.datetime.fromisoformat(last)
                    if shown.date() == now.date():
                        done.append((shown, r))
                except ValueError:
                    pass
        upcoming.sort(key=lambda x: x[0])
        done.sort(key=lambda x: x[0], reverse=True)
        return upcoming, done

    def refresh(self):
        now = datetime.datetime.now()
        upcoming, done = self._entries(now)
        self.counts[0].setText(str(len(upcoming)))
        self.counts[1].setText(str(len(done)))

        if upcoming:
            occ, r = upcoming[0]
            self.next_title.set_full_text(r.get("text", ""))
            self.next_count.setText(schedule.countdown(occ, now))
            self.next_when.set_full_text(f"{occ:%H:%M}  {schedule.describe_rule(r).split(' at ')[0]}")
            self.next_box.show()
        else:
            self.next_box.hide()

        body = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(body)
        # Room on the right so the scrollbar never covers the times
        lay.setContentsMargins(0, 4, theme.px(14), 8)
        lay.setSpacing(0)
        if self.tab == 0:
            self._fill_upcoming(lay, upcoming, now)
        else:
            self._fill_done(lay, done)
        lay.addStretch()
        self.scroll.setWidget(body)

    def _fill_upcoming(self, lay, upcoming, now):
        if not upcoming:
            self._empty(lay, "Add your first reminder and it will show up here.", True)
            return
        by_group = {g: [] for g in GROUPS}
        for occ, r in upcoming:
            by_group[schedule.group_of(occ, now)].append((occ, r))
        for group in GROUPS:
            if not by_group[group]:
                continue
            section = label(group, "section")
            section.setContentsMargins(8, theme.px(12), 0, theme.px(4))
            lay.addWidget(section)
            for occ, r in by_group[group]:
                lay.addWidget(ReminderRow(r, schedule.describe_rule(r), schedule.relative_label(occ, now),
                                          self.app.open_editor, self._delete))

    def _fill_done(self, lay, done):
        if not done:
            self._empty(lay, "Reminders shown today will appear here.", False)
            return
        for shown, r in done:
            lay.addWidget(ReminderRow(r, schedule.describe_rule(r), f"Shown {shown:%H:%M}", done=True))

    def _empty(self, lay, text, with_button):
        lay.addStretch()
        msg = label(text, "meta")
        msg.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        lay.addWidget(msg)
        if with_button:
            b = QtWidgets.QPushButton("New reminder")
            b.clicked.connect(lambda: self.app.open_editor(None))
            row = QtWidgets.QHBoxLayout()
            row.addStretch()
            row.addWidget(b)
            row.addStretch()
            lay.addSpacing(12)
            lay.addLayout(row)

    # ----- actions -----

    def _switch_tab(self, i):
        self.tab = i
        self.refresh()

    def _delete(self, reminder):
        text = reminder.get("text", "")
        if confirm(self, "Delete reminder?", f"“{text}” will be removed, including future repeats.",
                   "Delete reminder"):
            self.app.delete_reminder(reminder)

    # ----- placement and closing -----

    def place(self, tray_geometry):
        screen = QtWidgets.QApplication.screenAt(tray_geometry.center()) if tray_geometry.isValid() else None
        area = (screen or QtWidgets.QApplication.primaryScreen()).availableGeometry()
        self.move(area.right() - self.width() - 12, area.bottom() - self.height() - 12)

    def changeEvent(self, event):
        # Like Windows flyouts: close when the user clicks elsewhere (but not while a dialog of ours is open)
        if event.type() == QtCore.QEvent.Type.ActivationChange and not self.isActiveWindow():
            QtCore.QTimer.singleShot(150, self._close_if_inactive)
        super().changeEvent(event)

    def _close_if_inactive(self):
        if not self.isActiveWindow() and QtWidgets.QApplication.activeModalWidget() is None:
            self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
