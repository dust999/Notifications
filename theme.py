"""Colors, fonts, icons and the Windows glass backdrop for the redesigned UI.

Tokens come from design/NOTES.md (the approved mockup). Everything is plain PyQt6:
no extra UI library, to keep the tray app light.
"""
import ctypes
import os
import sys

from PyQt6 import QtCore, QtGui, QtSvg

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

_CAT_DARK = {"work": ("#b8b6d6", "rgba(176,172,224,0.10)"), "personal": ("#c9b8a3", "rgba(201,180,150,0.10)"),
             "health": ("#a3c2b8", "rgba(160,198,184,0.10)"), "shopping": ("#a9bcd2", "rgba(154,183,215,0.10)"),
             "none": ("#9aa3b0", "rgba(220,228,240,0.055)")}
_CAT_LIGHT = {"work": ("#5f5a8a", "rgba(105,95,160,0.08)"), "personal": ("#7a6047", "rgba(150,115,75,0.08)"),
              "health": ("#4a6e62", "rgba(75,120,100,0.08)"), "shopping": ("#4d6a8c", "rgba(80,115,160,0.08)"),
              "none": ("#5b6473", "rgba(30,40,60,0.045)")}


def _dark(accent, hover, on_accent, base, tint, glow=None):
    """Dark tokens from an accent and a base surface color (r, g, b) with its tint for overlays (r, g, b)."""
    r, g, b = base
    tr, tg, tb = tint
    return {
        "accent": accent, "accent_hover": hover, "on_accent": on_accent,
        "text": "#eef1f6", "text2": "#aeb5c2", "muted": "#8e96a4",
        "surface": f"rgba({r},{g},{b},0.88)", "surface_solid": f"rgb({r},{g},{b})",
        "popup": f"rgb({r + 8},{g + 8},{b + 10})", "selected": f"rgb({r + 19},{g + 20},{b + 24})",
        "hover": f"rgba({tr},{tg},{tb},0.065)", "divider": f"rgba({tr},{tg},{tb},0.10)",
        "edge": f"rgba({tr},{tg},{tb},0.15)", "input": "rgba(8,10,16,0.40)", "chip": f"rgba({tr},{tg},{tb},0.05)",
        "error": "#ffb4ab", "fullscreen": f"rgba({r - 12},{g - 12},{b - 12},0.90)", "glow": glow or accent,
        "cat": _CAT_DARK,
    }


def _light(accent, hover, base, tint):
    """Light tokens: cool light-gray surfaces (not white), lighter controls on top, blue accent."""
    r, g, b = base
    tr, tg, tb = tint
    lift = lambda d: f"rgb({min(r + d, 255)},{min(g + d, 255)},{min(b + d, 255)})"
    return {
        "accent": accent, "accent_hover": hover, "on_accent": "#ffffff",
        "text": "#1d222b", "text2": "#4b5363", "muted": "#5d6576",
        "surface": f"rgba({r},{g},{b},0.92)", "surface_solid": f"rgb({r},{g},{b})",
        "popup": lift(8), "selected": lift(14),
        "hover": f"rgba({tr},{tg},{tb},0.06)", "divider": f"rgba({tr},{tg},{tb},0.13)",
        "edge": "rgba(255,255,255,0.70)", "input": f"rgba(255,255,255,0.55)", "chip": f"rgba({tr},{tg},{tb},0.06)",
        "error": "#b3261e", "fullscreen": f"rgba({r - 4},{g - 4},{b - 3},0.94)", "glow": accent,
        "cat": _CAT_LIGHT,
    }


# Colors the user can give a reminder (payday green, bills red...): (name, dark theme, light theme).
# Brighter than the category colors on purpose: a colored reminder should stand out in the calendar.
REMINDER_COLORS = [
    ("red", "Red", "#f08585", "#c43c3c"),
    ("yellow", "Yellow", "#e6c86e", "#9a7410"),
    ("green", "Green", "#7fd19b", "#2c8a4e"),
    ("cyan", "Light blue", "#72cde4", "#16809a"),
    ("blue", "Blue", "#7f9cf2", "#2f55c8"),
    ("purple", "Purple", "#bba1f2", "#6a4cc4"),
]


def reminder_color(name):
    """QColor for a reminder color name in the current theme, or None for no color."""
    for key, _label, dark, light in REMINDER_COLORS:
        if key == name:
            return QtGui.QColor(dark if _dark_mode else light)
    return None


def badge_colors(category, color_name=None):
    """(symbol color '#rrggbb', fill QColor) for a category badge in the list and fullscreen views.
    A reminder's own color wins, toned a little toward grey: the same hue as in the calendar, calmer."""
    own = reminder_color(color_name)
    if own is None:
        symbol, tint = c("cat")[category]
        return qcolor(symbol).name(), qcolor(tint)
    grey = qcolor(c("text2"))
    mix = 0.25
    soft = QtGui.QColor(round(own.red() * (1 - mix) + grey.red() * mix),
                        round(own.green() * (1 - mix) + grey.green() * mix),
                        round(own.blue() * (1 - mix) + grey.blue() * mix))
    fill = QtGui.QColor(own)
    fill.setAlphaF(0.16 if _dark_mode else 0.13)
    return soft.name(), fill


# Color schemes: dark tokens, light tokens, and the tray/app tile gradient (top, bottom)
PALETTES = {
    "slate": (_dark("#86a8f4", "#a3bdf7", "#0c1a38", (27, 30, 39), (214, 226, 255)),
              _light("#2f5fcf", "#244db0", (228, 232, 240), (30, 50, 100)),
              ("#7b9cf2", "#3a5bc6")),
}
DEFAULT_PALETTE = "slate"

# Classic Segoe UI: "Segoe UI Variable" looks almost the same but costs ~50 MB of RAM when loaded
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else ".AppleSystemUIFont"
_current = PALETTES[DEFAULT_PALETTE][0]
_dark_mode = True
_palette = DEFAULT_PALETTE

# Text size setting: everything (fonts, controls, windows) scales with it
SIZES = {"normal": 1.0, "large": 1.15, "larger": 1.3}
DEFAULT_SIZE = "large"
_scale = SIZES[DEFAULT_SIZE]


def px(n):
    """A design size in pixels, scaled by the user's text size setting."""
    return round(n * _scale)


def system_prefers_dark():
    """Works on Windows and macOS: Qt reads the OS light/dark setting."""
    app = QtGui.QGuiApplication.instance()
    if app is not None:
        scheme = app.styleHints().colorScheme()
        if scheme != QtCore.Qt.ColorScheme.Unknown:
            return scheme == QtCore.Qt.ColorScheme.Dark
    return True


def set_mode(mode, palette=None, size=None):
    """mode: 'dark', 'light' or 'system'; palette: a key of PALETTES; size: a key of SIZES."""
    global _current, _dark_mode, _palette, _scale
    _scale = SIZES.get(size, SIZES[DEFAULT_SIZE])
    _palette = palette if palette in PALETTES else DEFAULT_PALETTE
    _dark_mode = system_prefers_dark() if mode == "system" else mode == "dark"
    _current = PALETTES[_palette][0 if _dark_mode else 1]
    _icon_cache.clear()


def c(name):
    return _current[name]


def is_dark():
    return _dark_mode


def qcolor(value):
    """QColor from '#rrggbb', 'rgb(r,g,b)' or 'rgba(r,g,b,a)'."""
    if value.startswith("rgb(") :
        return QtGui.QColor(*[int(x) for x in value[4:-1].split(",")])
    if value.startswith("rgba"):
        r, g, b, a = [x.strip() for x in value[5:-1].split(",")]
        return QtGui.QColor(int(r), int(g), int(b), round(float(a) * 255))
    return QtGui.QColor(value)


def font(size, weight=400):
    """Font at a design size; scaled by the text size setting."""
    f = QtGui.QFont(FONT_FAMILY)
    f.setPixelSize(px(size))
    f.setWeight(QtGui.QFont.Weight(weight))
    return f


# ---------- icons (SVG with currentColor, tinted per theme) ----------

_icon_cache = {}


def pixmap(name, color=None, size=20, dpr=None):
    color = color or c("text2")
    dpr = dpr or QtGui.QGuiApplication.primaryScreen().devicePixelRatio()
    key = (name, color, size, dpr)
    if key not in _icon_cache:
        with open(os.path.join(ICON_DIR, f"{name}.svg"), encoding="utf-8") as f:
            # Drawn bolder than the source (1.5) so small icons read clearly
            svg = f.read().replace("currentColor", qcolor(color).name()).replace(
                'stroke-width="1.5"', 'stroke-width="1.9"')
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
        pm = QtGui.QPixmap(round(size * dpr), round(size * dpr))
        pm.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pm)
        renderer.render(painter)
        painter.end()
        pm.setDevicePixelRatio(dpr)
        _icon_cache[key] = pm
    return _icon_cache[key]


def icon(name, color=None, size=20):
    return QtGui.QIcon(pixmap(name, color, size))


def taskbar_is_light():
    """The Windows taskbar has its own light/dark setting, separate from apps."""
    if sys.platform == "win32":
        try:
            import winreg
            key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                return winreg.QueryValueEx(k, "SystemUsesLightTheme")[0] == 1
        except OSError:
            return False
    return not system_prefers_dark()


def tray_icon():
    """Outline bell like the system tray icons: white on a dark taskbar, dark on a light one.
    Follows the taskbar, not the app's theme, so it is always visible."""
    color = "#1c1c1c" if taskbar_is_light() else "#ffffff"
    with open(os.path.join(ICON_DIR, "tray.svg"), encoding="utf-8") as f:
        source = f.read().replace("currentColor", color)
    result = QtGui.QIcon()
    for size in (16, 20, 24, 32, 40, 48):
        svg = source.replace('stroke-width="1.5"', f'stroke-width="{2.1 if size <= 24 else 1.8}"')
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.GlobalColor.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode())).render(p, QtCore.QRectF(0, 0, size, size))
        p.end()
        result.addPixmap(pm)
    return result


def tile_icon(palette=None):
    """Desktop and window icon: a white bell on a rounded square tile in the palette's color."""
    top, bottom = PALETTES[palette or _palette][2]
    result = QtGui.QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 256):
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.GlobalColor.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        g = QtGui.QLinearGradient(0, 0, size, size)
        g.setColorAt(0, QtGui.QColor(top))
        g.setColorAt(1, QtGui.QColor(bottom))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(g)
        inset = max(1, size // 16)
        p.drawRoundedRect(QtCore.QRectF(inset, inset, size - 2 * inset, size - 2 * inset), size * 0.24, size * 0.24)
        bell = round(size * (0.80 if size <= 20 else 0.68))
        with open(os.path.join(ICON_DIR, "tray.svg"), encoding="utf-8") as f:
            svg = f.read().replace("currentColor", "#ffffff").replace(
                'stroke-width="1.5"', f'stroke-width="{2.2 if size <= 20 else 2.0}"')
        QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode())).render(
            p, QtCore.QRectF((size - bell) / 2, (size - bell) / 2, bell, bell))
        p.end()
        result.addPixmap(pm)
    return result


# ---------- Windows 11 glass ----------

def _windows_build():
    return sys.getwindowsversion().build if sys.platform == "win32" else 0


def glass_supported():
    """System backdrop (Mica/Acrylic) needs Windows 11 22H2 or newer."""
    return _windows_build() >= 22621 and os.environ.get("QT_QPA_PLATFORM") != "offscreen"


def apply_glass(widget, kind="acrylic"):
    """Ask Windows to draw a blurred backdrop behind a translucent frameless window.
    Returns False when not available; the widget then paints a solid surface."""
    if not glass_supported():
        return False
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi

        class MARGINS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]

        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(-1, -1, -1, -1)))
        dark = ctypes.c_int(1 if is_dark() else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))      # immersive dark mode
        corner = ctypes.c_int(2)
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))  # rounded corners
        backdrop = ctypes.c_int({"mica": 2, "acrylic": 3}[kind])
        return dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop)) == 0
    except (OSError, AttributeError):
        return False


def style_title_bar(widget):
    """Native title bar in the app's colors: dark or light, and on Windows 11 the window's own color."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        dark = ctypes.c_int(1 if is_dark() else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))  # immersive dark mode
        if _windows_build() >= 22000:
            for attr, name in ((35, "surface_solid"), (36, "text")):  # caption color, caption text color
                col = qcolor(c(name))
                ref = ctypes.c_uint(col.red() | (col.green() << 8) | (col.blue() << 16))
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(ref), ctypes.sizeof(ref))
    except (OSError, AttributeError):
        pass


# ---------- global stylesheet ----------

def stylesheet():
    t = _current
    S = lambda n: f"{px(n)}px"
    return f"""
    /* No font-family here: in a stylesheet it makes Qt scan every system font (~45 MB).
       The font is set once with app.setFont() instead. */
    * {{ color: {t['text']}; }}
    QToolTip {{ background: {t['popup']}; color: {t['text']}; border: 1px solid {t['divider']}; padding: 4px 8px; }}
    QLabel {{ background: transparent; }}
    QLabel[role="h1"] {{ font-size: {S(24)}; font-weight: 650; }}
    QLabel[role="h2"] {{ font-size: {S(22)}; font-weight: 650; }}
    QLabel[role="next"] {{ font-size: {S(25)}; font-weight: 600; }}
    QLabel[role="caption"] {{ font-size: {S(13)}; color: {t['text2']}; font-weight: 500; }}
    QLabel[role="section"] {{ font-size: {S(12)}; color: {t['muted']}; font-weight: 500; }}
    QLabel[role="row"] {{ font-size: {S(14)}; font-weight: 600; }}
    QLabel[role="meta"] {{ font-size: {S(12)}; color: {t['text2']}; }}
    QLabel[role="accent"] {{ font-size: {S(13)}; color: {t['accent']}; font-weight: 600; }}
    QLabel[role="error"] {{ font-size: {S(13)}; color: {t['error']}; }}
    QLabel[role="field"] {{ font-size: {S(13)}; font-weight: 600; }}
    QLabel[role="count"] {{ font-size: {S(12)}; font-weight: 600; color: {t['text2']}; background: {t['chip']};
        border: 1px solid {t['divider']}; border-radius: {S(10)}; padding: 0 {S(7)};
        min-height: {S(20)}; max-height: {S(20)}; }}
    QLabel[role="body"] {{ font-size: {S(14)}; color: {t['text2']}; }}
    QPushButton {{ font-size: {S(14)}; font-weight: 600; border-radius: 8px; padding: 0 14px; min-height: {S(36)};
        background: {t['chip']}; border: 1px solid {t['divider']}; }}
    QPushButton:hover {{ background: {t['hover']}; }}
    QPushButton[kind="primary"] {{ background: {t['accent']}; color: {t['on_accent']}; border: none; }}
    QPushButton[kind="primary"]:hover {{ background: {t['accent_hover']}; }}
    QPushButton[kind="icon"] {{ background: transparent; border: none; padding: 0; min-height: 0;
        border-radius: 6px; }}
    QPushButton[kind="icon"]:hover {{ background: {t['hover']}; }}
    QPushButton[kind="tool"] {{ background: {t['chip']}; border: 1px solid {t['divider']}; padding: 0;
        min-height: 0; border-radius: 10px; }}
    QPushButton[kind="tool"]:hover {{ background: {t['hover']}; }}
    QPushButton[kind="chip"] {{ font-size: {S(13)}; font-weight: 500; min-height: {S(32)}; padding: 0 10px;
        border-radius: 6px; }}
    QPushButton[kind="chip"]:checked {{ border: 1px solid {t['accent']}; color: {t['accent']}; }}
    QFrame#segmented {{ background: {t['chip']}; border: 1px solid {t['divider']}; border-radius: 8px; }}
    QPushButton[kind="segment"] {{ font-size: {S(13)}; font-weight: 500; min-height: {S(30)}; padding: 0 8px;
        border: none; border-radius: 6px; background: transparent; color: {t['text2']}; }}
    QPushButton[kind="segment"]:checked {{ background: {t['selected']}; color: {t['text']}; font-weight: 600; }}
    QPushButton[kind="tab"] {{ font-size: {S(14)}; font-weight: 500; min-height: {S(34)}; padding: 0 2px;
        border: none; border-radius: 0; background: transparent; color: {t['text2']};
        border-bottom: 2px solid transparent; }}
    QPushButton[kind="tab"]:checked {{ color: {t['text']}; font-weight: 600; border-bottom: 2px solid {t['accent']}; }}
    QPushButton[kind="tab"]:hover {{ color: {t['text']}; }}
    QPushButton:focus {{ outline: none; border: 1px solid {t['accent']}; }}
    QPushButton[kind="tab"]:focus {{ border: none; border-bottom: 2px solid {t['accent']}; }}
    QFrame#divider {{ background: {t['divider']}; max-height: 1px; min-height: {S(3)}; border: none; }}
    QWidget#row {{ border-radius: 7px; }}
    QWidget#row:hover {{ background: {t['hover']}; }}
    QLineEdit, QTimeEdit, QDateEdit, QSpinBox, QComboBox {{ font-size: {S(14)}; background: {t['input']};
        border: 1px solid {t['divider']}; border-radius: 6px; padding: 0 10px; min-height: {S(36)};
        selection-background-color: {t['accent']}; selection-color: {t['on_accent']}; }}
    QLineEdit:focus, QTimeEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {t['accent']}; }}
    QLineEdit[invalid="true"] {{ border: 1px solid {t['error']}; }}
    QTimeEdit::up-button, QTimeEdit::down-button, QSpinBox::up-button, QSpinBox::down-button,
    QDateEdit::up-button, QDateEdit::down-button {{ width: 0; border: none; }}
    QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView, QListView#suggestions {{ background: {t['popup']}; border: 1px solid {t['divider']};
        selection-background-color: {t['selected']}; selection-color: {t['text']}; outline: none; padding: 4px; }}
    QCalendarWidget QWidget {{ background: {t['popup']}; alternate-background-color: {t['popup']}; }}
    QCalendarWidget QToolButton {{ color: {t['text']}; background: transparent; font-weight: 600; padding: 4px 8px; }}
    QCalendarWidget QAbstractItemView:enabled {{ color: {t['text']}; selection-background-color: {t['accent']};
        selection-color: {t['on_accent']}; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t['divider']}; border-radius: 3px; min-height: {S(32)}; }}
    QScrollBar::handle:vertical:hover {{ background: {t['muted']}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
    QCheckBox {{ font-size: {S(14)}; spacing: 8px; }}
    QMenu {{ background: {t['popup']}; border: 1px solid {t['divider']}; border-radius: 8px; padding: 4px;
        font-size: {S(14)}; }}
    QMenu::item {{ padding: 6px 24px 6px 10px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t['hover']}; }}
    QMenu::separator {{ height: 1px; background: {t['divider']}; margin: 4px 6px; }}
    """
