import os
from PyQt6 import QtWidgets, QtGui, QtCore

class FullscreenReminder(QtWidgets.QWidget):
    def __init__(self, text, icon_path, config):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setWindowOpacity(0.85)
        self.showFullScreen()

        fr_config = config["fullscreen_reminder"]
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(fr_config["bg_color"]))
        self.setPalette(palette)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addStretch(1)

        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        if icon_path and os.path.exists(icon_path):
            icon_label = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap(icon_path).scaled(64, 64, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(icon_label)

        text_label = QtWidgets.QLabel(text, self)
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet(f"color: {fr_config['text_color']}; font-size: 48px;")
        content_layout.addWidget(text_label)

        main_layout.addWidget(content_widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch(1)

        self.setLayout(main_layout)
        self.mousePressEvent = self.close_on_click

    def close_on_click(self, event):
        self.close()