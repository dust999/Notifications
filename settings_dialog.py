import winreg
import sys
import os
from PyQt6 import QtWidgets, QtGui

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, config_static, config_dynamic, parent, toggle_auto_run_callback, icon_path=None):
        super().__init__(parent)
        self.config_static = config_static
        self.config_dynamic = config_dynamic
        self.parent = parent
        self.toggle_auto_run_callback = toggle_auto_run_callback
        self.setWindowTitle(self.config_static["settings_dialog"]["window_title"])

        # Set window icon if provided
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog { 
                background-color: #1e1e1e; 
                color: #ffffff; 
                font-family: 'Segoe UI'; 
            }
            QCheckBox { 
                color: #ffffff; 
                font-size: 12px; 
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #444444;
                border-radius: 3px;
                background-color: #2e2e2e;
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #1a8c99;
            }
            QCheckBox::indicator:hover {
                border-color: #555555;
            }
            QLabel { 
                color: #ffffff; 
                font-size: 12px; 
            }
            QSpinBox {
                background-color: #2e2e2e;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QSpinBox:focus {
                border-color: #0d7377;
            }
            QPushButton {
                background-color: #2e2e2e;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
                border-color: #555555;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Auto-start checkbox
        self.auto_run_checkbox = QtWidgets.QCheckBox(self.config_static["settings_dialog"]["autostart_label"])
        self.auto_run_checkbox.setChecked(self.is_auto_start_enabled())
        self.auto_run_checkbox.stateChanged.connect(self.toggle_auto_run)
        layout.addWidget(self.auto_run_checkbox)

        # Spacing
        layout.addSpacing(8)

        # Interval setting
        interval_label = QtWidgets.QLabel(self.config_static["settings_dialog"]["interval_label"])
        layout.addWidget(interval_label)

        self.interval_spinbox = QtWidgets.QSpinBox()
        self.interval_spinbox.setRange(15, 3600)
        self.interval_spinbox.setSuffix(" sec")
        self.interval_spinbox.setValue(self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"])
        layout.addWidget(self.interval_spinbox)

        # Spacing before buttons
        layout.addSpacing(12)

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

    def is_auto_start_enabled(self):
        """Check if auto-start is currently enabled in Windows registry"""
        try:
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_READ) as reg_key:
                value, _ = winreg.QueryValueEx(reg_key, "ReminderApp")
                return bool(value)
        except (WindowsError, FileNotFoundError):
            return False

    def toggle_auto_run(self, state):
        """Toggle auto-start functionality"""
        enabled = bool(state)
        success = self.set_auto_start(enabled)

        if not success:
            # If setting failed, revert checkbox state
            self.auto_run_checkbox.blockSignals(True)
            self.auto_run_checkbox.setChecked(not enabled)
            self.auto_run_checkbox.blockSignals(False)

            # Show error message
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Failed to modify auto-start settings. Please check your permissions."
            )
        else:
            # Update config
            self.config_dynamic["settings_dialog"]["autostart"] = enabled
            # Call the callback if provided
            if self.toggle_auto_run_callback:
                self.toggle_auto_run_callback(enabled)

    def set_auto_start(self, enabled):
        """Set or remove auto-start registry entry"""
        try:
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

            with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as reg_key:
                if enabled:
                    # Get the path to the startup file
                    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

                    # Look for Start.bat in the same directory as the app
                    start_bat_path = os.path.join(current_dir, "Start.bat")

                    if os.path.exists(start_bat_path):
                        # Use the batch file if it exists
                        exe_path = f'"{start_bat_path}"'
                    elif getattr(sys, 'frozen', False):
                        # Running as compiled executable
                        exe_path = f'"{sys.executable}"'
                    else:
                        # Running as script - use pythonw to avoid console window
                        main_script = os.path.abspath(sys.argv[0])
                        if main_script.endswith('.pyw'):
                            # Use pythonw for .pyw files to avoid console window
                            python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                            exe_path = f'"{python_exe}" "{main_script}"'
                        else:
                            exe_path = f'"{sys.executable}" "{main_script}"'

                    # Set the registry value
                    winreg.SetValueEx(reg_key, "ReminderApp", 0, winreg.REG_SZ, exe_path)
                    print(f"Auto-start enabled with path: {exe_path}")
                else:
                    # Remove the registry value
                    try:
                        winreg.DeleteValue(reg_key, "ReminderApp")
                        print("Auto-start disabled")
                    except FileNotFoundError:
                        # Value doesn't exist, which is fine
                        pass

            return True
        except Exception as e:
            print(f"Error setting auto-start: {e}")
            return False

    def get_config_data(self):
        """Get updated configuration data"""
        self.config_dynamic["settings_dialog"]["reminder_check_interval_sec"] = self.interval_spinbox.value()
        self.config_dynamic["settings_dialog"]["autostart"] = self.auto_run_checkbox.isChecked()
        return self.config_dynamic