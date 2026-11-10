"""Small custom widgets for the redesigned UI (plain PyQt6, painted to match the mockup)."""
import datetime
import math

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


def is_quitting():
    return _quitting


def close_now(win):
    """Close a window that a new copy of itself replaces (it brings nothing back on closing)."""
    win._close_state = "now"
    win.close()


def no_os_animation(win):
    """Windows fades windows in and out on its own: off, so ours appear and go in one frame."""
    try:
        import ctypes
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(int(win.winId()), 3, ctypes.byref(on), ctypes.sizeof(on))
    except (OSError, AttributeError):
        pass


def _next_frame():
    """Block until Windows has put the next frame on screen."""
    try:
        import ctypes
        ctypes.windll.dwmapi.DwmFlush()
    except (OSError, AttributeError):
        pass


def wait_until_on_screen(win, limit_ms=120):
    """For a window just shown: return once it is really on screen. Windows reports a new
    window visible a moment after show(), and only then can Qt draw it."""
    handle = win.windowHandle()
    clock = QtCore.QElapsedTimer()
    clock.start()
    while handle is not None and not handle.isExposed() and clock.elapsed() < limit_ms:
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents, 5)
    win.repaint()
    _next_frame()


def appear_when_drawn(win, on_shown=None):
    """Call from showEvent. The window appears all at once, with no animation: it stays
    invisible until Windows has drawn it completely, then shows in one step. Shown plainly,
    a window first blinks gray or white (its glass or frame comes a frame before our content).
    `on_shown` runs once it is on screen (e.g. hide the window it replaces)."""
    no_os_animation(win)
    win.setWindowOpacity(0.0)
    win._on_shown = on_shown
    QtCore.QTimer.singleShot(0, lambda: appear_now(win))


def appear_now(win):
    """Finish appear_when_drawn right away (when the caller must know the window is up)."""
    try:
        if getattr(win, "_on_shown", False) is False:
            return   # already done
        on_shown, win._on_shown = win._on_shown, False
        if win.isVisible():
            wait_until_on_screen(win)
            _next_frame()          # the glass backdrop needs one more
        win.setWindowOpacity(1.0)
        if win.isVisible():
            _next_frame()
        if on_shown:
            on_shown()
    except RuntimeError:   # deleted meanwhile
        pass


_ghosts = set()   # entrances still playing; Python must hold them or they vanish mid-animation


class _Ghost(QtWidgets.QWidget):
    """A picture of a window in a see-through window of its own, drawn zoomed and faded.
    The entrance plays on it, so the real window never has to be scaled: meanwhile the real
    window is there, but invisible."""

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
        self.scale, self.opacity, self.dy = 1.0, 0.0, 0.0

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
            for i in range(2, 13, 2):
                p.setBrush(QtGui.QColor(0, 0, 0, round(12 * (1 - i / 14) ** 2)))
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


def zoom_in(win, origin=0.5, rise=0, start_scale=0.9, duration=260):
    """Call from showEvent: the window grows from a bit smaller (and `rise` px lower) while it
    fades in. `origin` is the point it grows from, as a share of its height: 0 top, 0.5 middle,
    1 bottom. Windows close at once, with no animation."""
    if _quitting or not animations_enabled():
        appear_when_drawn(win)
        return
    no_os_animation(win)
    win.setWindowOpacity(0.0)   # there (and drawn, glass and all), but unseen until the end
    win._on_shown = False
    shadow = not win.windowFlags() & QtCore.Qt.WindowType.NoDropShadowWindowHint
    ghost = _Ghost(_picture(win), win.geometry(), origin, getattr(win, "radius", 8) if shadow else None)
    _ghosts.add(ghost)
    ghost.destroyed.connect(lambda _=None, g=ghost: _ghosts.discard(g))
    no_os_animation(ghost)
    anim = QtCore.QVariantAnimation(ghost)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    def gone():
        try:
            return not win.isVisible()
        except RuntimeError:   # deleted
            return True

    def step(t):
        if gone():   # closed before the entrance ended: the picture goes with it
            anim.stop()
            ghost.close()
            return
        ghost.scale = start_scale + (1 - start_scale) * t
        ghost.opacity = min(t * 1.25, 1.0)
        ghost.dy = rise * (1 - t)
        ghost.update()

    def finish():
        if not gone():
            win.setWindowOpacity(1.0)
            _next_frame()   # the real window is on screen before the picture goes
        ghost.close()

    anim.valueChanged.connect(step)
    anim.finished.connect(finish)
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


class Switcher(QtWidgets.QWidget):
    """Shows one of its pages (or none). Switching fades the old page out and the new one in
    while the height eases to the new page's, quickly. Switching again midway carries on from
    wherever things are. `resized` is sent on every step, so the window can follow."""
    resized = QtCore.pyqtSignal()
    DURATION = 180

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        self.pages, self.effects = {}, {}
        self.current = None
        self.height_now = 0.0
        self.anim = QtCore.QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(self.DURATION)
        self.anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._step)
        self.anim.finished.connect(self._settle)

    def add(self, key, page):
        page.setParent(self)
        effect = QtWidgets.QGraphicsOpacityEffect(page)
        effect.setOpacity(0.0)
        page.setGraphicsEffect(effect)
        page.hide()
        page.installEventFilter(self)
        self.pages[key], self.effects[key] = page, effect

    def eventFilter(self, obj, event):
        # a page whose own content changed size (styled on first show, rows hidden): follow it
        if (event.type() == QtCore.QEvent.Type.LayoutRequest and obj is self.pages.get(self.current)
                and self.anim.state() != QtCore.QAbstractAnimation.State.Running):
            QtCore.QTimer.singleShot(0, self._refit)
        return False

    def _refit(self):
        if self.anim.state() == QtCore.QAbstractAnimation.State.Running:
            return
        height = self.page_height(self.current)
        page = self.pages.get(self.current)
        if page is not None:
            self._place(page, self.current)
        if height != round(self.height_now):
            self.height_now = height
            self.updateGeometry()
            self.resized.emit()

    def showEvent(self, event):
        super().showEvent(event)
        self._refit()   # sizes are right only once styled

    def page_height(self, key):
        page = self.pages.get(key)
        if page is None:
            return 0
        if page.hasHeightForWidth() and self.width() > 0:
            return page.heightForWidth(self.width())
        return page.sizeHint().height()

    def sizeHint(self):
        width = max([p.sizeHint().width() for p in self.pages.values()] or [0])
        return QtCore.QSize(width, round(self.height_now))

    def minimumSizeHint(self):
        return QtCore.QSize(0, round(self.height_now))

    def show_page(self, key, animate=True):
        if key == self.current and self.anim.state() != QtCore.QAbstractAnimation.State.Running:
            return
        self.current = key
        page = self.pages.get(key)
        if page is not None:
            page.show()
            page.raise_()
            self._place(page, key)
        self.from_height, self.to_height = self.height_now, self.page_height(key)
        self.from_opacity = {k: e.opacity() for k, e in self.effects.items()}
        self.anim.stop()
        if animate and animations_enabled() and self.window().isVisible():
            for e in self.effects.values():
                e.setEnabled(True)
            self.anim.start()
        else:
            self._step(1.0)
            self._settle()

    def _step(self, t):
        self.height_now = self.from_height + (self.to_height - self.from_height) * t
        for key, effect in self.effects.items():
            goal = 1.0 if key == self.current else 0.0
            start = self.from_opacity.get(key, 0.0)
            # the old page is gone by mid-way, the new one comes in over the whole time
            share = min(t * 2, 1.0) if goal == 0.0 else t
            effect.setOpacity(start + (goal - start) * share)
        self.updateGeometry()
        self.resized.emit()

    def _settle(self):
        for key, page in self.pages.items():
            if key == self.current:
                self.effects[key].setOpacity(1.0)
                self.effects[key].setEnabled(False)   # drawn directly again: crisp, no extra work
            else:
                self.effects[key].setOpacity(0.0)
                page.hide()
        self.height_now = self.page_height(self.current)
        self.updateGeometry()
        self.resized.emit()

    def _place(self, page, key):
        page.setGeometry(0, 0, self.width(), self.page_height(key))

    def resizeEvent(self, event):
        for key, page in self.pages.items():
            self._place(page, key)
        super().resizeEvent(event)


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
        self._glass()
        if not event.spontaneous():
            zoom_in(self)

    def _glass(self):
        if not self._has_glass:
            self._has_glass = theme.apply_glass(self, "acrylic")
            self.repaint()

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
        self._glass()
        if not event.spontaneous():
            if getattr(self, "entrance", True):
                zoom_in(self, origin=1.0, rise=theme.px(16))
            else:
                appear_when_drawn(self)

    def _glass(self):
        if self._glass_kind and not self._has_glass:
            self._has_glass = theme.apply_glass(self, self._glass_kind)
            self.repaint()

    def paintEvent(self, event):
        paint_surface(self, self._has_glass, self.radius, self.surface)



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


def _mix(a, b, t):
    """Color between a (t=0) and b (t=1)."""
    a, b = QtGui.QColor(a), QtGui.QColor(b)
    return QtGui.QColor.fromRgbF(*(x + (y - x) * t for x, y in zip(a.getRgbF(), b.getRgbF())))


class _CheckedGlow(QtCore.QObject):
    """Makes a chip's accent (border and text color) fade in when it is switched on and out
    when off; switched again midway, it turns back from where it is. While it fades, the chip
    gets the in-between colors itself, so there is still one label, drawn by the chip."""

    def __init__(self, button, off, on, edge):
        super().__init__(button)
        self.button = button
        self.off, self.on, self.edge = off, on, edge
        self.level = 1.0 if button.isChecked() else 0.0
        self.anim = QtCore.QVariantAnimation(self)
        self.anim.setDuration(170)
        self.anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._paint_level)
        self.anim.finished.connect(lambda: self.button.setStyleSheet(""))   # at rest: the usual look
        button.toggled.connect(self._toggled)

    def _toggled(self, on):
        self.anim.stop()
        if animations_enabled() and self.button.isVisible():
            self._paint_level(self.level)   # right away: the usual look would jump to the end
            self.anim.setStartValue(self.level)
            self.anim.setEndValue(1.0 if on else 0.0)
            self.anim.start()
        else:
            self.level = 1.0 if on else 0.0
            self.button.setStyleSheet("")

    def _paint_level(self, value):
        self.level = value
        css = lambda c: "rgba(%d,%d,%d,%.3f)" % (c.red(), c.green(), c.blue(), c.alphaF())
        on = theme.qcolor(theme.c(self.on))
        sheet = f"QPushButton {{ color: {css(_mix(theme.qcolor(theme.c(self.off)), on, value))}; }}"
        if self.edge:
            edge = _mix(theme.qcolor(theme.c("divider")), theme.qcolor(theme.c("accent")), value)
            sheet = (f"QPushButton {{ color: {css(_mix(theme.qcolor(theme.c(self.off)), on, value))};"
                     f" border: 1px solid {css(edge)}; }}"
                     f"QPushButton:focus {{ border: 1px solid {theme.c('accent')}; }}")
        self.button.setStyleSheet(sheet)


def fade_checked(button, off="text", on="accent", edge=True):
    """Switching a chip on or off fades its colors (text `off` to `on`, and the border to the
    accent if `edge`) instead of flipping them. They must match the button's stylesheet."""
    button._glow = _CheckedGlow(button, off, on, edge)
    return button


def crossfade(widget, duration=160):
    """Call right before changing what `widget` shows: the old look fades out over the new.
    Called again midway, it fades out from what is on screen at that moment."""
    old = getattr(widget, "_crossfade", None)
    if not animations_enabled() or not widget.isVisible():
        return
    cover = QtWidgets.QLabel(widget)
    cover.setPixmap(widget.grab())   # includes a cover still fading: no jump
    cover.setGeometry(widget.rect())
    cover.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    if old is not None:
        try:
            old.deleteLater()
        except RuntimeError:
            pass
    effect = QtWidgets.QGraphicsOpacityEffect(cover)
    cover.setGraphicsEffect(effect)
    anim = QtCore.QVariantAnimation(cover)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setDuration(duration)
    anim.valueChanged.connect(effect.setOpacity)
    anim.finished.connect(cover.deleteLater)
    widget._crossfade = cover
    cover.show()
    cover.raise_()
    anim.start()


class TabStrip(QtWidgets.QWidget):
    """Holds tab buttons (kind "tab") and draws the accent line under the checked one; the line
    slides to a tab when it is picked, and turns back if another is picked midway."""

    def __init__(self, group, parent=None):
        super().__init__(parent)
        self.group = group
        self._line = None
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._step)
        group.idToggled.connect(lambda i, on: on and self._slide())

    def watch(self, button):
        button.installEventFilter(self)
        fade_checked(button, off="text2", on="text", edge=False)

    def _target(self):
        b = self.group.checkedButton()
        if b is None:
            return None
        g = QtCore.QRectF(b.geometry())
        return QtCore.QRectF(g.left(), g.bottom() - 1, g.width(), 2)

    def _slide(self):
        target = self._target()
        if self._line is None or target is None or not self.isVisible() or not animations_enabled():
            self._anim.stop()
            self._line = target
            self.update()
            return
        self._from, self._to = QtCore.QRectF(self._line), target
        self._anim.stop()
        self._anim.start()

    def _step(self, t):
        a, b = self._from, self._to
        mix = lambda x, y: x + (y - x) * t
        self._line = QtCore.QRectF(mix(a.left(), b.left()), mix(a.top(), b.top()), mix(a.width(), b.width()), 2)
        self.update()

    def eventFilter(self, obj, event):
        if (event.type() in (QtCore.QEvent.Type.Move, QtCore.QEvent.Type.Resize)
                and obj is self.group.checkedButton()
                and self._anim.state() != QtCore.QAbstractAnimation.State.Running):
            self._line = self._target()
            self.update()
        return False

    def paintEvent(self, event):
        if self._line is None:
            self._line = self._target()
        if self._line is None:
            return
        p = QtGui.QPainter(self)
        p.fillRect(self._line, theme.qcolor(theme.c("accent")))
        p.end()


class Segmented(QtWidgets.QFrame):
    """One-of-many choice: Once / Daily / Weekly / ... The highlight slides over to the
    option picked; a click midway sends it on from wherever it is."""
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
            fade_checked(b, off="text2", on="text", edge=False)
            b.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            self.group.addButton(b, i)
            lay.addWidget(b)
            b.installEventFilter(self)   # buttons laid out anew: the highlight follows
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(self.changed)
        self.group.idToggled.connect(lambda i, on: on and self._slide())
        self._pill = None   # where the highlight is drawn (QRectF), None until laid out
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._step)

    def index(self):
        return self.group.checkedId()

    def set_index(self, i):
        self.group.button(i).setChecked(True)
        self.changed.emit(i)

    def slide_from(self, rect):
        """A copy that replaces another one: the highlight sets off from where the old one's was."""
        if rect is not None:
            self._pill = QtCore.QRectF(rect)
            self._slide()

    def _target(self):
        b = self.group.checkedButton()
        return QtCore.QRectF(b.geometry()) if b is not None else None

    def _slide(self):
        target = self._target()
        if (self._pill is None or target is None or not self.isVisible() or not animations_enabled()):
            self._anim.stop()
            self._pill = target
            self.update()
            return
        self._from, self._to = QtCore.QRectF(self._pill), target
        self._anim.stop()
        self._anim.start()

    def _step(self, t):
        a, b = self._from, self._to
        mix = lambda x, y: x + (y - x) * t
        self._pill = QtCore.QRectF(mix(a.left(), b.left()), mix(a.top(), b.top()),
                                   mix(a.width(), b.width()), mix(a.height(), b.height()))
        self.update()

    def eventFilter(self, obj, event):
        if (event.type() in (QtCore.QEvent.Type.Move, QtCore.QEvent.Type.Resize)
                and obj is self.group.checkedButton()
                and self._anim.state() != QtCore.QAbstractAnimation.State.Running):
            self._pill = self._target()
            self.update()
        return False

    def paintEvent(self, event):
        super().paintEvent(event)   # the track: background and border from the stylesheet
        if self._pill is None:
            self._pill = self._target()
        if self._pill is not None:
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(theme.qcolor(theme.c("selected")))
            p.drawRoundedRect(self._pill, 6, 6)
            p.end()


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
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on):
        # Slide only when the user flips it; when set up before showing, jump into place
        if animations_enabled() and self.isVisible():
            self._anim.stop()   # flipped again midway: from where the thumb is now
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
        t = self._pos   # colors follow the thumb: off at 0, on at 1
        accent, muted = theme.qcolor(theme.c("accent")), theme.qcolor(theme.c("muted"))
        fill = QtGui.QColor(accent)
        fill.setAlphaF(fill.alphaF() * t)
        p.setPen(QtGui.QPen(_mix(muted, accent, t), 1))
        p.setBrush(fill)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 8
        x = r.left() + 4 + self._pos * (r.width() - 8 - d)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(_mix(muted, theme.qcolor(theme.c("on_accent")), t))
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
        self._level = 0.0   # 0 not picked .. 1 picked: the ring fades between
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_level)
        self.toggled.connect(self._toggled)

    def _set_level(self, value):
        self._level = value
        self.update()

    def _toggled(self, on):
        self._anim.stop()   # picked again midway: back from where it is
        if animations_enabled() and self.isVisible():
            self._anim.setStartValue(self._level)
            self._anim.setEndValue(1.0 if on else 0.0)
            self._anim.start()
        else:
            self._set_level(1.0 if on else 0.0)

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
        hover = self.underMouse() or self.hasFocus()
        level = self._level
        if level > 0.001 or hover:
            ring = theme.qcolor(theme.c("muted"))
            if not hover:
                ring.setAlphaF(ring.alphaF() * level)   # no hover ring underneath: fade from nothing
            ring = _mix(ring, theme.qcolor(theme.c("text")), level)
            p.setPen(QtGui.QPen(ring, 1 + level))
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


class _DropDown(QtWidgets.QFrame):
    """Base of the small pickers that drop down under a field (date, time): rounded popup
    surface, grows in from the field and shrinks away when closed. A click outside closes it."""

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.WindowType.Popup | QtCore.Qt.WindowType.FramelessWindowHint
                         | QtCore.Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        # A click outside only closes the popup; it isn't passed on to what's underneath
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoMouseReplay)

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
        zoom_in(self, origin=getattr(self, "_origin", 0.0))


class DatePopup(_DropDown):
    """Small month calendar that drops down under a calendar button. Click a day to pick it.
    Arrows move the day, PageUp/PageDown the month, Enter picks, Esc closes."""
    picked = QtCore.pyqtSignal(object)

    def __init__(self, date, parent=None):
        super().__init__(parent)
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


class _Wheel(QtWidgets.QWidget):
    """One spinning column of TimePopup (hours or minutes). The values loop round; the chosen
    one sits in the accent band in the middle. Turn it with the mouse wheel, drag it, or click
    a row to bring it to the middle; Up/Down when it has the focus (its title lights up)."""
    changed = QtCore.pyqtSignal(int)   # the value now in the band
    ROWS = 5

    def __init__(self, title, values, value, parent=None):
        super().__init__(parent)
        self.title = title
        self.row_h, self.head_h = theme.px(36), theme.px(26)
        self.setFixedSize(theme.px(104), self.head_h + self.row_h * self.ROWS)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_pos)
        self._wheel_rest = 0      # touchpads send the wheel in small pieces
        self._press = None
        self._hover = None
        self.set_values(values, value)

    def set_values(self, values, value):
        """Show `values`, with the one nearest to `value` in the band (no animation)."""
        self._anim.stop()
        self.values = list(values)
        i = min(range(len(self.values)), key=lambda k: abs(self.values[k] - value))
        self.pos, self.target = float(i), i
        self.update()

    def value(self):
        return self.values[round(self.pos) % len(self.values)]

    def _set_pos(self, pos):
        before = self.value()
        self.pos = pos
        self.update()
        if self.value() != before:
            self.changed.emit(self.value())

    def spin_to(self, target):
        """Turn to row `target` (counted without wrapping, so it always takes the short way)."""
        self.target = target
        self._anim.stop()
        if not animations_enabled() or not self.isVisible():
            self._set_pos(float(target))
            return
        self._anim.setStartValue(self.pos)
        self._anim.setEndValue(float(target))
        self._anim.start()

    def _mid(self):
        return self.head_h + self.row_h * self.ROWS / 2

    def _row_at(self, y):
        """Rows from the middle band to the point `y` (0 = the band itself)."""
        return round((y - self._mid()) / self.row_h)

    # ----- mouse and keys -----

    def wheelEvent(self, event):
        self._wheel_rest += event.angleDelta().y()
        steps = int(self._wheel_rest / 120)
        if steps:
            self._wheel_rest -= steps * 120
            self.spin_to(self.target - steps)   # wheel up = earlier values come down into the band
        event.accept()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        self._anim.stop()
        self._press = (event.position().y(), self.pos, False)

    def mouseMoveEvent(self, event):
        y = event.position().y()
        if self._press is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            start_y, start_pos, dragged = self._press
            if dragged or abs(y - start_y) > theme.px(4):
                self._press = (start_y, start_pos, True)
                self._hover = None
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                self._set_pos(start_pos - (y - start_y) / self.row_h)
            return
        hover = self._row_at(y) if y > self.head_h else None
        if hover != self._hover:
            self._hover = hover
            self.update()

    def mouseReleaseEvent(self, event):
        if self._press is None:
            return
        dragged = self._press[2]
        self._press = None
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        here = round(self.pos)
        if dragged:
            self.spin_to(here)
        elif event.position().y() > self.head_h:
            self.spin_to(here + self._row_at(event.position().y()))

    def leaveEvent(self, event):
        self._hover = None
        self.update()

    def keyPressEvent(self, event):
        step = {QtCore.Qt.Key.Key_Up: -1, QtCore.Qt.Key.Key_Down: 1,
                QtCore.Qt.Key.Key_PageUp: -3, QtCore.Qt.Key.Key_PageDown: 3}.get(event.key())
        if step:
            self.spin_to(self.target + step)
        else:
            super().keyPressEvent(event)   # Left/Right, Enter, Esc go on to the popup

    def focusInEvent(self, event):
        self.update()

    def focusOutEvent(self, event):
        self.update()

    # ----- painting -----

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w = self.width()
        p.setFont(theme.font(13, 600 if self.hasFocus() else 500))
        p.setPen(theme.qcolor(theme.c("text" if self.hasFocus() else "muted")))
        p.drawText(QtCore.QRectF(0, 0, w, self.head_h - theme.px(4)), int(QtCore.Qt.AlignmentFlag.AlignCenter), self.title)

        body = QtCore.QRectF(0, self.head_h, w, self.row_h * self.ROWS).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = theme.px(8)
        p.setPen(QtGui.QPen(theme.qcolor(theme.c("divider")), 1))
        p.setBrush(theme.qcolor(theme.c("input")))
        p.drawRoundedRect(body, radius, radius)
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(body, radius, radius)
        p.setClipPath(clip)

        mid, rh, inset = self._mid(), self.row_h, theme.px(5)
        band = QtCore.QRectF(inset, mid - rh / 2 + 2, w - 2 * inset, rh - 4)
        if self._hover:   # a row you can click (the band itself needs no hover)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(theme.qcolor(theme.c("hover")))
            p.drawRoundedRect(band.translated(0, self._hover * rh), radius - 2, radius - 2)

        n, first = len(self.values), math.floor(self.pos)
        rows = [(first + k, mid + (first + k - self.pos) * rh) for k in range(-3, 4)]
        p.setFont(theme.font(15, 500))
        for i, y in rows:   # rows fade out towards the top and bottom edges
            p.setOpacity(max(0.0, 1.0 - abs(i - self.pos) * 0.3))
            p.setPen(theme.qcolor(theme.c("text")))
            p.drawText(QtCore.QRectF(0, y - rh / 2, w, rh), int(QtCore.Qt.AlignmentFlag.AlignCenter),
                       f"{self.values[i % n]:02d}")
        p.setOpacity(1.0)

        # The band, with the numbers passing through it drawn again on top of it
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(theme.c("accent")))
        p.drawRoundedRect(band, radius - 2, radius - 2)
        inside = QtGui.QPainterPath()
        inside.addRoundedRect(band, radius - 2, radius - 2)
        p.setClipPath(inside)
        p.setFont(theme.font(15, 650))
        p.setPen(theme.qcolor(theme.c("on_accent")))
        for i, y in rows:
            p.drawText(QtCore.QRectF(0, y - rh / 2, w, rh), int(QtCore.Qt.AlignmentFlag.AlignCenter),
                       f"{self.values[i % n]:02d}")
        p.end()


class TimePopup(_DropDown):
    """Drops down under the Time field: two spinning columns, hours and minutes, minutes in
    5-minute steps or every minute. The field follows along as they turn; ✓, Enter or a click
    outside keeps the time, ✕ or Esc puts the old one back. Left/Right switch columns."""
    picked = QtCore.pyqtSignal(object)   # datetime.time, on every change

    def __init__(self, time, parent=None):
        super().__init__(parent)
        self.original = time
        step = 5 if time.minute % 5 == 0 else 1
        root = QtWidgets.QVBoxLayout(self)
        m = theme.px(12)
        root.setContentsMargins(m, theme.px(8), m, m)
        root.setSpacing(theme.px(10))
        cols = QtWidgets.QHBoxLayout()
        cols.setSpacing(theme.px(8))
        self.hours = _Wheel("Hour", range(24), time.hour)
        self.minutes = _Wheel("Minute", range(0, 60, step), time.minute)
        for wheel in (self.hours, self.minutes):
            wheel.changed.connect(self._emit)
            cols.addWidget(wheel)
        root.addLayout(cols)

        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(theme.px(6))
        self.steps = Segmented(["5 min", "1 min"])
        for b in self.steps.group.buttons():
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.steps.set_index(0 if step == 5 else 1)
        self.steps.changed.connect(self._set_step)
        self.steps.setToolTip("Minutes in 5-minute steps, or every minute")
        bottom.addWidget(self.steps)
        bottom.addStretch()
        side = theme.px(38)
        cancel = IconButton("close", "Cancel (Esc)", 38, 18)
        cancel.setProperty("kind", "tool")
        cancel.setFixedSize(side, side)
        cancel.clicked.connect(self.cancel)
        ok = IconButton("check", "Done (Enter)", 38, 20, color=theme.c("on_accent"))
        ok.setFixedSize(side, side)
        ok.setStyleSheet(f"QPushButton {{ background: {theme.c('accent')}; border: none; border-radius: 10px; }}"
                         f"QPushButton:hover {{ background: {theme.c('accent_hover')}; }}")
        ok.clicked.connect(self.close)
        for b in (cancel, ok):
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)   # the keys stay with the columns
            bottom.addWidget(b)
        root.addLayout(bottom)

    def value(self):
        return datetime.time(self.hours.value(), self.minutes.value())

    def _emit(self, _=None):
        self.picked.emit(self.value())

    def _set_step(self, i):
        minute = self.minutes.value()
        self.minutes.set_values(range(0, 60, 5 if i == 0 else 1), minute)
        if self.minutes.value() != minute:
            self._emit()

    def cancel(self):
        self.picked.emit(self.original)
        self.close()

    def show_under(self, widget):
        super().show_under(widget)
        self.hours.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (QtCore.Qt.Key.Key_Left, QtCore.Qt.Key.Key_Right):
            (self.hours if key == QtCore.Qt.Key.Key_Left else self.minutes).setFocus()
        elif key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self.close()
        elif key == QtCore.Qt.Key.Key_Escape:
            self.cancel()
        else:
            super().keyPressEvent(event)
