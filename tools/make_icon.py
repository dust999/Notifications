"""Rebuild icons/notify.ico (desktop shortcut icon) from the app's tile icon.

Run from the project folder:  python tools/make_icon.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6 import QtCore, QtWidgets  # noqa: E402

app = QtWidgets.QApplication(["make_icon", "-platform", "offscreen"])
import theme  # noqa: E402

palette = sys.argv[1] if len(sys.argv) > 1 else theme.DEFAULT_PALETTE
icon = theme.tile_icon(palette=palette)
entries = []
for size in (16, 20, 24, 32, 40, 48, 64, 256):
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    icon.pixmap(size, size).toImage().save(buf, "PNG")
    entries.append((size, bytes(buf.data())))

# ICO file holding PNG images (supported since Windows Vista)
offset = 6 + 16 * len(entries)
table, blobs = b"", b""
for size, png in entries:
    dim = 0 if size >= 256 else size
    table += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
    offset += len(png)
    blobs += png
out = os.path.join(theme.ICON_DIR, "notify.ico")
with open(out, "wb") as f:
    f.write(struct.pack("<HHH", 0, 1, len(entries)) + table + blobs)
print(f"{out}: {len(entries)} sizes, {offset} bytes, palette {palette}")
