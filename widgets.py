"""Small custom widgets for the redesigned UI (plain PyQt6, painted to match the mockup)."""
import datetime

from PyQt6 import QtCore, QtGui, QtWidgets

import schedule
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


_quitting = False


def app_quitting():
    """Called right before the app quits: windows close at once, without fading out.
    (Qt cancels a quit if a window delays its closing.)"""
    global _quitting
    _quitting = True


def fade_window(win, appear, offset=8, duration=None, on_done=None):
    """Fade a top-level window in (sliding `offset` px into place) or out (sliding half of
    that away). `on_done` runs when it ends. Without animations it runs at once."""
    old = getattr(win, "_fade_anim", None)
    if old is not None:
        old.stop()
    if not animations_enabled():
        win.setWindowOpacity(1.0 if appear else 0.0)
        if on_done:
            on_done()
        return
    duration = duration or (190 if appear else 140)
    here = win.pos()
    if appear:
        start_pos, end_pos, start_op, end_op = here + QtCore.QPoint(0, offset), here, 0.0, 1.0
        win.move(start_pos)
        win.setWindowOpacity(0.0)
    else:
        start_pos, end_pos, start_op, end_op = here, here + QtCore.QPoint(0, offset // 2), win.windowOpacity(), 0.0
    group = QtCore.QParallelAnimationGroup(win)
    for prop, start, stop in ((b"windowOpacity", start_op, end_op), (b"pos", start_pos, end_pos)):
        if prop == b"pos" and not offset:
            continue
        a = QtCore.QPropertyAnimation(win, prop, group)
        a.setDuration(duration)
        a.setStartValue(start)
        a.setEndValue(stop)
        a.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic if appear else QtCore.QEasingCurve.Type.InCubic)
        group.addAnimation(a)
    if on_done:
        group.finished.connect(on_done)
    win._fade_anim = group
    group.start()


def close_with_fade(win, event, offset=8):
    """For closeEvent: the first close() fades the window out and closes it for real afterwards.
    Returns True when the event was put off (the caller returns at once)."""
    state = getattr(win, "_close_state", None)
    if state == "closing":
        event.ignore()          # already fading out: the second close() comes when it ends
        return True
    if state == "now" or _quitting or not win.isVisible() or not animations_enabled():
        return False
    win._close_state = "closing"
    event.ignore()

    def finish():
        win._close_state = "now"
        win.close()
    fade_window(win, False, offset, on_done=finish)
    return True


def close_now(win):
    """Close without an exit animation (a window replaced by a new copy of itself)."""
    win._close_state = "now"
    win.close()


_ghosts = set()   # pictures still playing; Python must hold them or they vanish mid-animation


class _Ghost(QtWidgets.QWidget):
    """A picture of a window in a see-through window of its own, drawn zoomed and faded.
    Entrances and exits play on it, so the real window never has to be scaled: while it comes
    in, the real window is there but invisible; on the way out the real one is already gone."""

    def __init__(self, picture, geometry, origin, radius=None):
        super().__init__(None, QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
                         | QtCore.Qt.WindowType.WindowStaysOnTopHint
                         | QtCore.Qt.WindowType.WindowTransparentForInput
                         | QtCore.Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.pad = theme.px(20)   # room for the slide
        self.setGeometry(geometry.adjusted(-self.pad, -self.pad, self.pad, self.pad))
        self.picture, self.origin = picture, origin
        self.radius = radius   # rounded windows get a soft shadow, like the one Windows gives them
        self.scale, self.opacity, self.dy = 1.0, 1.0, 0.0

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        p.setOpacity(self.opacity)
        size = QtCore.QSizeF(self.picture.size()) / self.picture.devicePixelRatio()
        pivot = QtCore.QPointF(self.pad + size.width() / 2, self.pad + size.height() * self.origin)
        p.translate(pivot.x(), pivot.y() + self.dy)
        p.scale(self.scale, self.scale)
        p.translate(-pivot)
        body = QtCore.QRectF(QtCore.QPointF(self.pad, self.pad), size)
        if self.radius is not None:
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            steps = 12
            for i in range(1, steps + 1):
                p.setBrush(QtGui.QColor(0, 0, 0, round(9 * (1 - i / (steps + 1)) ** 2)))
                p.drawRoundedRect(body.adjusted(-i, -i + 2, i, i + 2), self.radius + i, self.radius + i)
        p.drawPixmap(body.topLeft(), self.picture)
        p.end()


def _picture(win):
    """The window as it looks, on a solid surface (the picture has no blurred glass behind it)."""
    glass = getattr(win, "_has_glass", False)
    win._has_glass = False
    if win.layout() is not None:
        win.layout().activate()   # sizes set just before showing are laid out in the picture too
    try:
        return win.grab()
    finally:
        win._has_glass = glass


def zoom_window(win, appear, origin=0.5, rise=0, on_done=None):
    """Entrance: the window grows from a bit smaller (and `rise` px lower) while it fades in.
    Exit: it shrinks a little and fades out. `origin` is the point it grows from, as a share
    of its height: 0 top, 0.5 middle, 1 bottom. Call it from showEvent (the window is about to
    appear) or right before the window hides. `on_done` runs once the real window is shown."""
    old = getattr(win, "_ghost", None)
    if old is not None:
        try:
            old.close()
        except RuntimeError:
            pass
        win._ghost = None
    if _quitting or not animations_enabled() or getattr(win, "_close_state", None) == "now":
        if on_done:
            on_done()
        return
    shadow = not win.windowFlags() & QtCore.Qt.WindowType.NoDropShadowWindowHint
    ghost = _Ghost(_picture(win), win.geometry(), origin, getattr(win, "radius", 8) if shadow else None)
    _ghosts.add(ghost)
    ghost.destroyed.connect(lambda _=None, g=ghost: _ghosts.discard(g))
    s0, s1, o0, o1, d0, d1 = (0.9, 1.0, 0.0, 1.0, rise, 0) if appear else (1.0, 0.94, 1.0, 0.0, 0, rise / 2)
    anim = QtCore.QVariantAnimation(ghost)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(260 if appear else 190)
    anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic if appear else QtCore.QEasingCurve.Type.OutQuad)

    def step(t):
        ghost.scale = s0 + (s1 - s0) * t
        ghost.opacity = o0 + (o1 - o0) * (min(t * 1.25, 1.0) if appear else t)
        ghost.dy = d0 + (d1 - d0) * t
        ghost.update()

    def finish():
        if appear:
            try:
                if on_done:
                    on_done()
                win.setWindowOpacity(1.0)
                win._ghost = None
            except RuntimeError:   # the window was deleted meanwhile
                pass
            QtCore.QTimer.singleShot(40, ghost.close)  # the real window is drawn before the picture goes
        else:
            ghost.close()

    anim.valueChanged.connect(step)
    anim.finished.connect(finish)
    if appear:
        win.setWindowOpacity(0.0)
        win._ghost = ghost
    step(0.0)
    ghost.show()
    ghost.repaint()
    anim.start()


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
        screen = (self.parentWidget() or self).screen().availableGeometry()
        self.move(screen.center() - self.rect().center())
        if event.spontaneous():
            self._glass()
        else:
            zoom_window(self, True, on_done=self._glass)   # the glass goes on once it's in place

    def _glass(self):
        if not self._has_glass:
            self._has_glass = theme.apply_glass(self, "acrylic")
            self.repaint()

    def done(self, result):
        """Accept / reject / Esc: the dialog closes at once; its picture shrinks and fades."""
        if self.isVisible():
            zoom_window(self, False)
        super().done(result)

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
        if getattr(self, "_entrance", False):
            self._entrance = False
            zoom_window(self, True, origin=1.0, rise=theme.px(16), on_done=self._glass)
        else:
            self._glass()

    def _glass(self):
        if self._glass_kind and not self._has_glass:
            self._has_glass = theme.apply_glass(self, self._glass_kind)
            self.repaint()

    def paintEvent(self, event):
        paint_surface(self, self._has_glass, self.radius, self.surface)

    def fade_in(self):
        """Show with an entrance: rises from the taskbar, growing as it fades in."""
        self._entrance = True
        self.show()

    def closeEvent(self, event):
        if self.isVisible():
            zoom_window(self, False, origin=1.0, rise=theme.px(16))
        super().closeEvent(event)


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
        start = schedule.week_start_of(first)
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
        for i, name in enumerate("MTWTFSS"[wd] for wd in schedule.week_order()):
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
        # A click outside only closes the popup; it isn't passed on to what's underneath
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoMouseReplay)
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
        self._origin = 0.0 if pos.y() > widget.mapToGlobal(QtCore.QPoint(0, 0)).y() else 1.0
        self.show()
        self.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        zoom_window(self, True, origin=getattr(self, "_origin", 0.0))

    def closeEvent(self, event):
        if self.isVisible():
            zoom_window(self, False, origin=getattr(self, "_origin", 0.0))
        super().closeEvent(event)
