"""Fullscreen reminder: covers the screen the user is working on until they click or press Esc."""
from PyQt6 import QtCore, QtGui, QtWidgets

import schedule
import theme
from widgets import CategoryBadge, label, zoom_in


class FullscreenReminder(QtWidgets.QWidget):
    closed = QtCore.pyqtSignal()

    def __init__(self, reminder, scheduled=None, note=None):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
                            | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(reminder.get("text", "Reminder"))
        self._has_glass = False

        screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos()) or QtWidgets.QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        title_px = theme.px(64 if screen.geometry().height() >= 900 else 52)

        root = QtWidgets.QVBoxLayout(self)
        root.addStretch(3)
        content = QtWidgets.QVBoxLayout()
        content.setSpacing(0)
        content.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        badge = CategoryBadge(schedule.category_of(reminder), size=64, icon_size=34, radius=18,
                              color=reminder.get("color"))
        content.addWidget(badge, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        content.addSpacing(28)

        title = label(reminder.get("text", ""))
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        # A fixed width lets the wrapped label compute its real height (no clipped second line)
        title.setFixedWidth(min(1100, screen.geometry().width() - 160))
        title.setStyleSheet(f"font-size: {title_px}px; font-weight: 650;")
        content.addWidget(title, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        content.addSpacing(14)

        if scheduled is not None:
            when = f"Scheduled for {schedule.WEEKDAYS[scheduled.weekday()]}, " \
                   f"{schedule.MONTHS[scheduled.month - 1]} {scheduled.day} at {scheduled:%H:%M}"
            sub = label(note or when)
            sub.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            sub.setStyleSheet(f"font-size: {theme.px(17)}px; color: {theme.c('text2')};")
            content.addWidget(sub, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        content.addSpacing(36)

        done = QtWidgets.QPushButton("  Done")
        done.setProperty("kind", "primary")
        done.setIcon(theme.icon("check", theme.c("on_accent"), theme.px(18)))
        done.setIconSize(QtCore.QSize(theme.px(18), theme.px(18)))
        done.setFixedSize(theme.px(160), theme.px(46))
        done.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self.close)
        content.addWidget(done, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        root.addLayout(content)
        root.addStretch(4)

        hint = label("Click anywhere or press Esc to close", "meta")
        hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)
        root.addSpacing(40)
        done.setFocus()

    def show(self):
        super().show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._has_glass:
            self._has_glass = theme.apply_glass(self, "acrylic")
        if not event.spontaneous():
            zoom_in(self, start_scale=1.0, duration=240)   # a plain fade in

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        fill = theme.qcolor(theme.c("fullscreen"))
        if not self._has_glass:
            fill.setAlpha(max(fill.alpha(), 235))
        p.fillRect(self.rect(), fill)
        p.end()

    def mousePressEvent(self, event):
        self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
