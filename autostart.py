"""Start the app at Windows logon via the per-user Run registry key."""
import os
import sys

if sys.platform == "win32":
    import winreg
# macOS later: a LaunchAgent plist in ~/Library/LaunchAgents instead of the registry

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "NotifyApp"
# Older versions also wrote this second entry, which started a broken extra copy of the app.
LEGACY_VALUE_NAMES = ("ReminderApp",)

APP_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.pyw")


def _command():
    """pythonw.exe runs the app without a console window."""
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw
    return f'"{exe}" "{APP_SCRIPT}"'


def is_enabled():
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False


def set_enabled(enabled):
    """Turn autostart on or off. Raises OSError if the registry can't be changed."""
    if sys.platform != "win32":
        raise OSError("Autostart is only implemented for Windows so far")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def repair():
    """Run once on startup: remove legacy entries that point at this app and make
    our entry point at this copy of the app (the folder may have moved)."""
    if sys.platform != "win32":
        return
    try:
        legacy_found = False
        access = winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, access) as key:
            for name in LEGACY_VALUE_NAMES:
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                except FileNotFoundError:
                    continue
                # Only touch entries that really launch this app.
                if "app.pyw" in str(value).lower():
                    winreg.DeleteValue(key, name)
                    legacy_found = True
        if legacy_found or is_enabled():
            set_enabled(True)
    except OSError as e:
        print(f"Warning: could not check autostart entries: {e}")
