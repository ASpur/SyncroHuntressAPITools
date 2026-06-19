#!/usr/bin/env python3
"""GUI entry point for SyncroHuntressAPITools."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme import Theme


def _create_app_icon() -> QIcon:
    """Render the ⇄ glyph to a pixmap for use as a window icon."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#2f6db3"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 12, 12)
    font = QFont()
    font.setPointSize(28)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "\u21c4")
    painter.end()
    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Syncro Huntress Comparison Tool")
    app.setOrganizationName("SyncroHuntressAPITools")
    app.setWindowIcon(_create_app_icon())

    Theme.instance().apply(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
