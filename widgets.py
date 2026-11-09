"""Small custom widgets for the redesigned UI (plain PyQt6, painted to match the mockup)."""
import datetime

from PyQt6 import QtCore, QtGui, QtWidgets

import theme


def label(text, role=None, parent=None):
    lbl = QtWidgets.QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    return lbl


class ElidedLabel(QtWidgets.QLabel):
    """One-line label that shortens itself with '…' to whatever width it gets.
    It never forces its parent wider, so long titles can't push a row under the scrollbar."""

    def __init__(self, text="", role=None, parent=None):
        super().__init__(parent)
        if role:
            self.setProperty("role", role)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        self._full = ""
        self.set_full_text(text)

    def set_full_text(self, text):
        self._full = text
        self.setToolTip(text)
        self._elide()

    def full_text(self):
        return self._full

    def minimumSizeHint(self):
        return QtCore.QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def _elide(self):
        width = max(self.width(), 10)
        super().setText(self.fontMetrics().elidedText(self._full, QtCore.Qt.TextElideMode.ElideRight, width))


def divider():
    line = QtWidgets.QFrame()
    line.setObjectName("divider")
    return line


def animations_enabled():
    """Respect the Windows 'Animation effects' setting."""
    try:
        import ctypes
        value = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0)  # SPI_GETCLIENTAREAANIMATION
        return bool(value.value)
    except (OSError, AttributeError):
        return True


def paint_surface(widget, has_glass, radius, surface="surface"):
    """Rounded window body: translucent tint over OS glass, or solid without glass."""
    p = QtGui.QPainter(widget)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    rect = QtCore.QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
    fill = theme.qcolor(theme.c(surface))
    if not has_glass:
        fill.setAlpha(255)
    p.setPen(QtGui.QPen(theme.qcolor(theme.c("edge")), 1) if radius else QtCore.Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, radius, radius)
    p.end()


class GlassDialog(QtWidgets.QDialog):
    """Modal version of GlassWindow (editor, confirmations)."""

    def __init__(self, parent=None, radius=13):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Dialog)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.radius = radius
        self._has_glass = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._has_glass:
            self._has_glass = theme.apply_glass(self, "acrylic")
        screen = (self.parentWidget() or self).screen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    def paintEvent(self, event):
        paint_surface(self, self._has_glass, self.radius)

    def mousePressEvent(self, event):
        self._drag = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton and hasattr(self, "_drag"):
            self.move(event.globalPosition().toPoint() - self._drag)


def confirm(parent, title, text, action):
    """Small 'Delete reminder?' style confirmation. Returns True if confirmed."""
    dlg = GlassDialog(parent)
    dlg.setFixedWidth(theme.px(380))
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(24, 22, 24, 20)
    lay.setSpacing(8)
    lay.addWidget(label(title, "h2"))
    body = label(text, "body")
    body.setWordWrap(True)
    lay.addWidget(body)
    lay.addSpacing(12)
    row = QtWidgets.QHBoxLayout()
    row.addStretch()
    cancel = QtWidgets.QPushButton("Cancel")
    ok = QtWidgets.QPushButton(action)
    ok.setProperty("kind", "primary")
    cancel.clicked.connect(dlg.reject)
    ok.clicked.connect(dlg.accept)
    row.addWidget(cancel)
    row.addWidget(ok)
    lay.addLayout(row)
    cancel.setFocus()
    return dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted


class GlassWindow(QtWidgets.QWidget):
    """Frameless rounded window. On Windows 11 the OS draws a blurred backdrop
    and we paint a translucent tint on top; elsewhere the tint is painted solid."""

    def __init__(self, parent=None, radius=12, glass="acrylic", flags=None):
        super().__init__(parent)
        self.setWindowFlags(flags or (QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.radius = radius
        self._glass_kind = glass
        self._has_glass = False
        self.surface = "surface"

    def showEvent(self, event):
        super().showEvent(event)
        if self._glass_kind and not self._has_glass:
            self._has_glass = theme.apply_glass(self, self._glass_kind)

    def paintEvent(self, event):
        paint_surface(self, self._has_glass, self.radius, self.surface)

    def fade_in(self, offset=8, duration=200):
        """One short entrance: fade and slide up a few pixels."""
        if not animations_enabled():
            self.show()
            return
        end = self.pos()
        self.move(end + QtCore.QPoint(0, offset))
        self.setWindowOpacity(0.0)
        self.show()
        group = QtCore.QParallelAnimationGroup(self)
        for prop, start, stop in ((b"windowOpacity", 0.0, 1.0), (b"pos", end + QtCore.QPoint(0, offset), end)):
            a = QtCore.QPropertyAnimation(self, prop, self)
            a.setDuration(duration)
            a.setStartValue(start)
            a.setEndValue(stop)
            a.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            group.addAnimation(a)
        group.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)


class IconButton(QtWidgets.QPushButton):
    def __init__(self, icon_name, tooltip, size=34, icon_size=20, color=None, parent=None):
        super().__init__(parent)
        self.setProperty("kind", "icon")
        size, icon_size = theme.px(size), theme.px(icon_size)
        # The stylesheet's min-height would undo setFixedSize, so the size is also
        # reported as the size hint (layouts then keep the button square)
        self._side = size
        self.setFixedSize(size, size)
        self.setIcon(theme.icon(icon_name, color or theme.c("text2"), icon_size))
        self.setIconSize(QtCore.QSize(icon_size, icon_size))
        # Mouse clicks don't leave a focus frame; Tab still reaches it
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def sizeHint(self):
        return QtCore.QSize(self._side, self._side)

    def minimumSizeHint(self):
        return self.sizeHint()


class CategoryBadge(QtWidgets.QWidget):
    """Category symbol in a muted tinted rounded square; in the reminder's own color if it has one."""

    def __init__(self, category, size=40, icon_size=22, radius=10, parent=None, color=None):
        super().__init__(parent)
        self.category, self.icon_size, self.radius = category, theme.px(icon_size), theme.px(radius)
        self.color = color
        self.setFixedSize(theme.px(size), theme.px(size))
        self.dimmed = False

    def paintEvent(self, event):
        symbol, tint = theme.badge_colors(self.category, self.color)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.dimmed:
            p.setOpacity(0.5)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(tint)
        p.drawRoundedRect(QtCore.QRectF(self.rect()), self.radius, self.radius)
        name = "check" if self.dimmed else f"cat-{self.category}"
        pm = theme.pixmap(name, symbol, self.icon_size)
        x = (self.width() - self.icon_size) / 2
        p.drawPixmap(QtCore.QPointF(x, (self.height() - self.icon_size) / 2), pm)
        p.end()


class Segmented(QtWidgets.QFrame):
    """One-of-many choice: Once / Daily / Weekly / ..."""
    changed = QtCore.pyqtSignal(int)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QtWidgets.QButtonGroup(self)
        for i, text in enumerate(options):
            b = QtWidgets.QPushButton(text)
            b.setProperty("kind", "segment")
            b.setCheckable(True)
            b.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            self.group.addButton(b, i)
            lay.addWidget(b)
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(self.changed)

    def index(self):
        return self.group.checkedId()

    def set_index(self, i):
        self.group.button(i).setChecked(True)
        self.changed.emit(i)


class Toggle(QtWidgets.QAbstractButton):
    """Pill switch with a sliding thumb."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(theme.px(44), theme.px(22))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._pos = 0.0
        self._anim = QtCore.QPropertyAnimation(self, b"thumb", self)
        self._anim.setDuration(150)
        self.toggled.connect(self._animate)

    def _animate(self, on):
        # Slide only when the user flips it; when set up before showing, jump into place
        if animations_enabled() and self.isVisible():
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(1.0 if on else 0.0)
            self._anim.start()
        else:
            self.thumb = 1.0 if on else 0.0

    def get_thumb(self):
        return self._pos

    def set_thumb(self, value):
        self._pos = value
        self.update()

    thumb = QtCore.pyqtProperty(float, get_thumb, set_thumb)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        on = self.isChecked()
        p.setPen(QtGui.QPen(theme.qcolor(theme.c("accent") if on else theme.c("muted")), 1))
        p.setBrush(theme.qcolor(theme.c("accent")) if on else QtCore.Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 8
        x = r.left() + 4 + self._pos * (r.width() - 8 - d)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(theme.c("on_accent") if on else theme.c("muted")))
        p.drawEllipse(QtCore.QRectF(x, r.center().y() - d / 2, d, d))
        p.end()


class NextUpGlow(QtWidgets.QWidget):
    """Container for the 'Next up' block with one static accent glow behind it."""

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        # Elliptical glow stretched to the block and fully faded before any edge
        # Small and faint: a hint of color behind the badge, not a spotlight
        g = QtGui.QRadialGradient(QtCore.QPointF(0.2, 0.5), 0.2)
        g.setCoordinateMode(QtGui.QGradient.CoordinateMode.ObjectBoundingMode)
        col = theme.qcolor(theme.c("glow"))
        col.setAlpha(22 if theme.is_dark() else 14)
        g.setColorAt(0, col)
        col.setAlpha(0)
        g.setColorAt(1, col)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRect(self.rect())
        p.end()


class ColorSwatch(QtWidgets.QAbstractButton):
    """Round color choice for a reminder. `color_name` None = no color (an empty ring with a slash)."""

    def __init__(self, color_name, tooltip, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.setCheckable(True)
        self.setFixedSize(theme.px(34), theme.px(34))
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QtCore.QRectF(self.rect())
        inner = r.adjusted(theme.px(6), theme.px(6), -theme.px(6), -theme.px(6))
        color = theme.reminder_color(self.color_name)
        if color is None:
            p.setPen(QtGui.QPen(theme.qcolor(theme.c("muted")), 1.5))
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawEllipse(inner.adjusted(1, 1, -1, -1))
            p.drawLine(QtCore.QPointF(inner.left() + inner.width() * 0.2, inner.bottom() - inner.height() * 0.2),
                       QtCore.QPointF(inner.right() - inner.width() * 0.2, inner.top() + inner.height() * 0.2))
        else:
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(inner)
        if self.isChecked() or self.underMouse() or self.hasFocus():
            ring = theme.qcolor(theme.c("text" if self.isChecked() else "muted"))
            p.setPen(QtGui.QPen(ring, 2 if self.isChecked() else 1))
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawEllipse(r.adjusted(2, 2, -2, -2))
        p.end()


def chevron_icon(angle, size=18):
    """Left/right arrows: the chevron-down icon turned (90 = left, -90 = right)."""
    down = theme.pixmap("chevron-down", theme.c("text2"), theme.px(size))
    pm = down.transformed(QtGui.QTransform().rotate(angle), QtCore.Qt.TransformationMode.SmoothTransformation)
    pm.setDevicePixelRatio(down.devicePixelRatio())
    return QtGui.QIcon(pm)


_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]


class _MonthGrid(QtWidgets.QWidget):
    """Painted Monday-first month for DatePopup: today ringed, the chosen day filled with the accent."""
    clicked = QtCore.pyqtSignal(object)

    def __init__(self, popup):
        super().__init__(popup)
        self.popup = popup
        self.hover = None
        self.setMouseTracking(True)
        self.setFixedSize(theme.px(7 * 38), theme.px(24 + 6 * 34))

    def _cells(self):
        first = self.popup.month
        start = first - datetime.timedelta(days=first.weekday())
        cw, rh, head = self.width() / 7, theme.px(34), theme.px(24)
        for i in range(42):
            r, c = divmod(i, 7)
            yield start + datetime.timedelta(days=i), QtCore.QRectF(c * cw, head + r * rh, cw, rh)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        cw = self.width() / 7
        p.setFont(theme.font(12, 500))
        p.setPen(theme.qcolor(theme.c("muted")))
        for i, name in enumerate("MTWTFSS"):
            p.drawText(QtCore.QRectF(i * cw, 0, cw, theme.px(24)), int(QtCore.Qt.AlignmentFlag.AlignCenter), name)
        today = datetime.date.today()
        for d, rect in self._cells():
            side = min(rect.width(), rect.height()) - theme.px(4)
            circle = QtCore.QRectF(rect.center().x() - side / 2, rect.center().y() - side / 2, side, side)
            chosen = d == self.popup.selected
            if chosen or d == self.hover:
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.setBrush(theme.qcolor(theme.c("accent" if chosen else "hover")))
                p.drawEllipse(circle)
            if d == today and not chosen:
                p.setPen(QtGui.QPen(theme.qcolor(theme.c("accent")), 1.5))
                p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                p.drawEllipse(circle.adjusted(1, 1, -1, -1))
            inside = d.month == self.popup.month.month
            color = "on_accent" if chosen else ("text" if inside else "muted")
            p.setPen(theme.qcolor(theme.c(color)))
            p.setFont(theme.font(13, 650 if chosen or d == today else 400))
            p.drawText(rect, int(QtCore.Qt.AlignmentFlag.AlignCenter), str(d.day))
        p.end()

    def _date_at(self, pos):
        for d, rect in self._cells():
            if rect.contains(pos):
                return d
        return None

    def mouseMoveEvent(self, event):
        d = self._date_at(event.position())
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor if d else QtCore.Qt.CursorShape.ArrowCursor)
        if d != self.hover:
            self.hover = d
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def mousePressEvent(self, event):
        d = self._date_at(event.position())
        if d is not None and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(d)


class DatePopup(QtWidgets.QFrame):
    """Small month calendar that drops down under a calendar button. Click a day to pick it.
    Arrows move the day, PageUp/PageDown the month, Enter picks, Esc closes."""
    picked = QtCore.pyqtSignal(object)

    def __init__(self, date, parent=None):
        super().__init__(parent, QtCore.Qt.WindowType.Popup | QtCore.Qt.WindowType.FramelessWindowHint
                         | QtCore.Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.selected = date
        self.month = date.replace(day=1)
        root = QtWidgets.QVBoxLayout(self)
        m = theme.px(12)
        root.setContentsMargins(m, theme.px(10), m, m)
        root.setSpacing(theme.px(6))
        head = QtWidgets.QHBoxLayout()
        prev = IconButton("chevron-down", "Previous month", 32, 18)
        prev.setIcon(chevron_icon(90))
        prev.clicked.connect(lambda: self.shift(-1))
        nxt = IconButton("chevron-down", "Next month", 32, 18)
        nxt.setIcon(chevron_icon(-90))
        nxt.clicked.connect(lambda: self.shift(1))
        self.title = label("", "row")
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        head.addWidget(prev)
        head.addWidget(self.title, 1)
        head.addWidget(nxt)
        root.addLayout(head)
        self.grid = _MonthGrid(self)
        self.grid.clicked.connect(self._pick)
        root.addWidget(self.grid)
        self._sync()

    def _sync(self):
        self.title.setText(f"{_MONTH_NAMES[self.month.month - 1]} {self.month.year}")
        self.grid.update()

    def shift(self, months):
        y, mo = divmod(self.month.month - 1 + months, 12)
        self.month = self.month.replace(year=self.month.year + y, month=mo + 1)
        self._sync()

    def _pick(self, d):
        self.picked.emit(d)
        self.close()

    def keyPressEvent(self, event):
        step = {QtCore.Qt.Key.Key_Left: -1, QtCore.Qt.Key.Key_Right: 1,
                QtCore.Qt.Key.Key_Up: -7, QtCore.Qt.Key.Key_Down: 7}.get(event.key())
        if step:
            self.selected += datetime.timedelta(days=step)
            self.month = self.selected.replace(day=1)
            self._sync()
        elif event.key() in (QtCore.Qt.Key.Key_PageUp, QtCore.Qt.Key.Key_PageDown):
            self.shift(-1 if event.key() == QtCore.Qt.Key.Key_PageUp else 1)
        elif event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self._pick(self.selected)
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        self.shift(-1 if event.angleDelta().y() > 0 else 1)

    def paintEvent(self, event):
        paint_surface(self, False, theme.px(10), "popup")

    def show_under(self, widget):
        """Open below `widget` (above it if there's no room), kept on its screen."""
        self.adjustSize()
        area = widget.screen().availableGeometry()
        pos = widget.mapToGlobal(QtCore.QPoint(0, widget.height() + theme.px(4)))
        if pos.y() + self.height() > area.bottom():
            pos = widget.mapToGlobal(QtCore.QPoint(0, -self.height() - theme.px(4)))
        pos.setX(min(max(pos.x(), area.left()), area.right() - self.width()))
        self.move(pos)
        self.show()
        self.setFocus()
