import winreg
from PyQt6 import QtWidgets

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, config_static, config_dynamic, parent, toggle_auto_run_callback, icon_path=None):
        super().__init__(parent)
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.parent = parent
        self.toggle_auto_run_callback = toggle_auto_run_callback
        self.setWindowTitle(self.config_static["settings_dialog"]["window_title"])
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        self.auto_run_checkbox = QtWidgets.QCheckBox(self.config_static["settings_dialog"]["autostart_label"])
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_READ) as reg_key:
                value, _ = winreg.QueryValueEx(reg_key, "ReminderApp")
                self.auto_run_checkbox.setChecked(bool(value))
        except WindowsError:
            pass
        self.auto_run_checkbox.stateChanged.connect(self.toggle_auto_run)
        layout.addWidget(self.auto_run_checkbox)

        interval_label = QtWidgets.QLabel(self.config_static["settings_dialog"]["interval_label"])
        layout.addWidget(interval_label)
        self.interval_spinbox = QtWidgets.QSpinBox()
        self.interval_spinbox.setRange(15, 3600)
        self.interval_spinbox.setValue(self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"])
        layout.addWidget(self.interval_spinbox)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def toggle_auto_run(self, state):
        enabled = bool(state)
        self.toggle_auto_run_callback(enabled)

    def get_config_data(self):
        self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"] = self.interval_spinbox.value()
        return self.config_dynamic