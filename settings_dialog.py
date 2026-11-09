import os
from PyQt6 import QtWidgets, QtGui
import autostart
from utils import save_json

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, config_static, config_dynamic, parent, data_manager=None, icon_path=None):
        super().__init__(parent)
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.parent = parent
        self.data_manager = data_manager
        self.setWindowTitle(self.config_static["settings_dialog"]["window_title"])

        # Set window icon if provided
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Apply dark theme styling with f-string to avoid .format() issues
        arrow_up_path = os.path.join(os.path.abspath("icons"), "arrow-up-white.svg").replace("\\", "/")
        arrow_down_path = os.path.join(os.path.abspath("icons"), "arrow-down-white.svg").replace("\\", "/")
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: #1e1e1e; 
                color: #ffffff; 
                font-family: 'Segoe UI', Arial, sans-serif; 
            }}
            QCheckBox {{ 
                color: #ffffff; 
                font-size: 12px; 
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid #444444;
                border-radius: 3px;
                background-color: #2e2e2e;
            }}
            QCheckBox::indicator:checked {{
                background-color: #0d7377;
                border-color: #1a8c99;
            }}
            QCheckBox::indicator:hover {{
                border-color: #555555;
            }}
            QLabel {{ 
                color: #ffffff; 
                font-size: 12px; 
            }}
            QSpinBox {{
                padding-right: 30px;
                min-height: 30px;
                font-size: 16px;
                color: #ffffff;
                background-color: #2e2e2e;
                border: 1px solid #444444;
                border-radius: 4px;
            }}
            QSpinBox:focus {{
                border-color: #0d7377;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 24px;
                height: 18px;
                border: none;
                background: transparent;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: #444444;
            }}
            QSpinBox::up-arrow {{
                width: 16px;
                height: 16px;
                image: url("{arrow_up_path}");
            }}
            QSpinBox::down-arrow {{
                width: 16px;
                height: 16px;
                image: url("{arrow_down_path}");
            }}
            QPushButton {{
                background-color: #2e2e2e;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: 500;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #3e3e3e;
                border-color: #555555;
            }}
            QPushButton:pressed {{
                background-color: #1e1e1e;
            }}
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Auto-start checkbox
        self.auto_run_checkbox = QtWidgets.QCheckBox(self.config_static["settings_dialog"]["autostart_label"])
        # Applied in accept(), so Cancel really cancels
        self.auto_run_checkbox.setChecked(autostart.is_enabled())
        layout.addWidget(self.auto_run_checkbox)

        # Spacing
        layout.addSpacing(8)

        # Interval setting
        interval_label = QtWidgets.QLabel(self.config_static["settings_dialog"]["interval_label"])
        layout.addWidget(interval_label)

        self.interval_spinbox = QtWidgets.QSpinBox()
        self.interval_spinbox.setRange(5, 3600)
        self.interval_spinbox.setSuffix(" sec")
        self.interval_spinbox.setValue(self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"])
        layout.addWidget(self.interval_spinbox)

        # Spacing before buttons
        layout.addSpacing(12)

        # Clear Backlog button
        clear_backlog_btn = QtWidgets.QPushButton("Clear Backlog")
        clear_backlog_btn.clicked.connect(self.clear_backlog)
        layout.addWidget(clear_backlog_btn)

        # Buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())

    def get_config_data(self):
        """Get updated configuration data"""
        self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"] = self.interval_spinbox.value()
        self.config_dynamic["settings_dialog"]["autostart"] = self.auto_run_checkbox.isChecked()
        return self.config_dynamic

    def accept(self):
        try:
            autostart.set_enabled(self.auto_run_checkbox.isChecked())
        except OSError:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Failed to change autostart settings. Please check your access rights."
            )
            return
        self.save_position()
        super().accept()

    def reject(self):
        self.save_position()
        super().reject()

    def restore_position(self):
        pos = self.config_dynamic["settings_dialog"].get("window_pos")
        if pos:
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            x = min(pos.get("x", 0), screen.width() - pos.get("width", self.width()))
            y = max(0, min(pos.get("y", 0), screen.height() - pos.get("height", self.height())))
            self.move(x, y)
            if "width" in pos and "height" in pos:
                self.resize(pos["width"], pos["height"])

    def save_position(self):
        pos = self.pos()
        size = self.size()
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.config_dynamic["settings_dialog"]["window_pos"] = {
            "x": pos.x(),
            "y": pos.y(),
            "width": size.width(),
            "height": size.height()
        }
        save_json(self.config_static["paths"]["config_dynamic_path"], self.config_dynamic)

    def closeEvent(self, event):
        self.save_position()
        super().closeEvent(event)

    def clear_backlog(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear Backlog",
            "Are you sure you want to clear all backlog suggestions? This cannot be undone.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Go through the data manager: it keeps the backlog cached in memory and
            # would write the old list back on the next save if only the file were cleared.
            if self.data_manager:
                self.data_manager.update_backlog([])
            else:
                save_json(self.config_static["paths"]["backlog_path"], [])
            QtWidgets.QMessageBox.information(self, "Backlog Cleared", "Backlog has been cleared.")