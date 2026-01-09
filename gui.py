#!/usr/bin/env python3
"""GUI entry point for SyncroHuntressAPITools."""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Syncro Huntress Comparison Tool")
    app.setOrganizationName("SyncroHuntressAPITools")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
