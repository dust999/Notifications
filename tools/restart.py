"""Restart the running Notify, e.g. after an update: ask it to save and exit, then start it again.

Run from anywhere:  python tools/restart.py
A copy started before restart support existed doesn't react to the request; it is closed by force
after a short wait (reminders are saved on every change, so nothing is lost).
"""
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = tempfile.gettempdir()
LOCK = os.path.join(TEMP, "NotifyApp.lock")          # held by the running copy (QLockFile, first line = PID)
REQUEST = os.path.join(TEMP, "NotifyApp", "quit")    # watched by the running copy

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.OpenProcess.restype = wintypes.HANDLE
SYNCHRONIZE, QUERY_LIMITED = 0x00100000, 0x1000


def _process_name(pid):
    handle = kernel32.OpenProcess(QUERY_LIMITED, False, pid)
    if not handle:
        return ""
    try:
        buf, size = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        return os.path.basename(buf.value).lower() if ok else ""
    finally:
        kernel32.CloseHandle(handle)


def running_pid():
    """PID of the running Notify, or None."""
    try:
        with open(LOCK, encoding="utf-8", errors="replace") as f:
            first = f.readline().strip()
    except OSError:
        return None
    if not first.isdigit():
        return None
    pid = int(first)
    return pid if _process_name(pid).startswith("python") else None   # a dead PID may be reused


def wait_exit(pid, seconds):
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return True
    try:
        return kernel32.WaitForSingleObject(handle, int(seconds * 1000)) == 0
    finally:
        kernel32.CloseHandle(handle)


def start():
    """Start Notify the way the user does: the desktop shortcut, through Explorer, so the new
    copy doesn't belong to (and die with) whatever ran this script."""
    shortcut = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "Notify.lnk")
    target = shortcut if os.path.exists(shortcut) else os.path.join(APP_DIR, "Start.bat")
    subprocess.Popen(["explorer.exe", target])


def main():
    old = running_pid()
    if old:
        os.makedirs(os.path.dirname(REQUEST), exist_ok=True)
        with open(REQUEST, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
        if wait_exit(old, 8):
            print(f"Notify (PID {old}) saved and closed")
        else:
            subprocess.run(["taskkill", "/PID", str(old), "/F"], capture_output=True)
            wait_exit(old, 5)
            print(f"Notify (PID {old}) didn't answer the request (older version): closed by force")
    else:
        print("Notify wasn't running")
    start()
    for _ in range(60):
        time.sleep(0.25)
        new = running_pid()
        if new and new != old:
            print(f"Notify started (PID {new})")
            return 0
    print("Notify didn't start within 15 s: check the tray, or run Start.bat")
    return 1


if __name__ == "__main__":
    sys.exit(main())
