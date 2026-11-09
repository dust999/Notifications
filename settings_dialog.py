from PyQt6 import QtCore, QtWidgets

import autostart
import theme
from utils import save_json
from widgets import GlassDialog, IconButton, Segmented, Toggle, confirm, divider, label

THEMES = ["system", "dark", "light"]
SIZES = ["normal", "large", "larger"]


def _index(options, value, default):
    return options.index(value) if value in options else options.index(default)


class SettingsDialog(GlassDialog):
    """Appearance changes apply at once (on_preview); Cancel puts the old look back."""

    def __init__(self, config_static, config_dynamic, parent=None, data_manager=None, on_preview=None):
        super().__init__(parent)
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.data_manager = data_manager
        self.on_preview = on_preview
        self.setWindowTitle("Settings")
        settings = config_dynamic.setdefault("settings_dialog", {})
        self.original = {k: settings.get(k) for k in ("theme", "palette", "text_size")}
        self.pending = {
            "theme": settings.get("theme", "system"),
            # Only one color scheme is left; an old saved "steel" becomes the default
            "palette": settings.get("palette") if settings.get("palette") in theme.PALETTES else theme.DEFAULT_PALETTE,
            "text_size": settings.get("text_size", theme.DEFAULT_SIZE),
            "autostart": autostart.is_enabled(),
            "interval": settings.get("reminder_check_interval_sec", 10),
        }
        self.outer = QtWidgets.QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.body = None
        self._build()

    # ----- layout (rebuilt after every appearance change, so sizes and colors update at once) -----

    def _build(self):
        if self.body is not None:
            self.pending["autostart"] = self.autostart.isChecked()
            self.pending["interval"] = self.interval.value()
            self.body.hide()
            self.body.deleteLater()
        self.setFixedWidth(theme.px(420))
        self.body = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(self.body)
        root.setContentsMargins(theme.px(24), theme.px(20), theme.px(24), theme.px(20))
        root.setSpacing(theme.px(6))

        head = QtWidgets.QHBoxLayout()
        head.addWidget(label("Settings", "h2"))
        head.addStretch()
        close = IconButton("close", "Close", 32, 18)
        close.clicked.connect(self.reject)
        head.addWidget(close)
        root.addLayout(head)
        root.addSpacing(theme.px(8))

        self.theme_choice = self._segmented(root, "Appearance", ["System", "Dark", "Light"],
                                            _index(THEMES, self.pending["theme"], "system"), "theme", THEMES)
        self.size_choice = self._segmented(root, "Text size", ["Normal", "Large", "Larger"],
                                           _index(SIZES, self.pending["text_size"], theme.DEFAULT_SIZE),
                                           "text_size", SIZES)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(label("Start with Windows", "field"))
        row.addStretch()
        # Applied in accept(), so Cancel really cancels
        self.autostart = Toggle()
        self.autostart.setAccessibleName("Start with Windows")
        self.autostart.setChecked(self.pending["autostart"])
        row.addWidget(self.autostart)
        root.addLayout(row)
        root.addSpacing(theme.px(10))

        root.addWidget(label("Check for due reminders every", "field"))
        self.interval = QtWidgets.QSpinBox()
        self.interval.setRange(5, 3600)
        self.interval.setSuffix(" sec")
        self.interval.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.interval.setFixedWidth(theme.px(120))
        self.interval.setValue(self.pending["interval"])
        root.addWidget(self.interval)
        root.addSpacing(theme.px(10))

        clear_row = QtWidgets.QHBoxLayout()
        clear_row.addWidget(label("Title suggestions", "field"))
        clear_row.addStretch()
        clear = QtWidgets.QPushButton("Clear")
        clear.clicked.connect(self.clear_backlog)
        clear_row.addWidget(clear)
        root.addLayout(clear_row)

        root.addSpacing(theme.px(12))
        root.addWidget(divider())
        root.addSpacing(theme.px(10))
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QtWidgets.QPushButton("Save")
        save.setProperty("kind", "primary")
        save.setMinimumWidth(theme.px(96))
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self.outer.addWidget(self.body)
        self.adjustSize()
        self.update()

    def _segmented(self, root, title, options, index, key, values):
        root.addWidget(label(title, "field"))
        seg = Segmented(options)
        seg.set_index(index)
        seg.changed.connect(lambda i: self._appearance_changed(key, values[i]))
        root.addWidget(seg)
        root.addSpacing(theme.px(10))
        return seg

    def _appearance_changed(self, key, value):
        if self.pending[key] == value:
            return
        self.pending[key] = value
        if self.on_preview:
            self.on_preview(self.pending["theme"], self.pending["palette"], self.pending["text_size"])
        # Rebuild after the click finishes (the clicked button is part of what gets replaced)
        QtCore.QTimer.singleShot(0, self._build)

    # ----- results -----

    def get_config_data(self):
        """Get updated configuration data"""
        settings = self.config_dynamic.setdefault("settings_dialog", {})
        settings["reminder_check_interval_sec"] = self.interval.value()
        settings["autostart"] = self.autostart.isChecked()
        settings["theme"] = self.pending["theme"]
        settings["palette"] = self.pending["palette"]
        settings["text_size"] = self.pending["text_size"]
        return self.config_dynamic

    def accept(self):
        try:
            autostart.set_enabled(self.autostart.isChecked())
        except OSError:
            confirm(self, "Couldn't change autostart",
                    "Windows didn't let Notify change the startup setting. Check your access rights.", "OK")
            return
        super().accept()

    def reject(self):
        changed = any(self.pending[k] != (self.original[k] or d) for k, d in
                      (("theme", "system"), ("palette", theme.DEFAULT_PALETTE), ("text_size", theme.DEFAULT_SIZE)))
        if changed and self.on_preview:
            self.on_preview(self.original["theme"] or "system", self.original["palette"], self.original["text_size"])
        super().reject()

    def clear_backlog(self):
        if not confirm(self, "Clear suggestions?",
                       "Titles you used before will no longer be suggested. This can't be undone.", "Clear"):
            return
        # Go through the data manager: it keeps the backlog cached in memory and
        # would write the old list back on the next save if only the file were cleared.
        if self.data_manager:
            self.data_manager.update_backlog([])
        else:
            save_json(self.config_static["paths"]["backlog_path"], [])
