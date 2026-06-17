"""Main application window: single window hosting the comparison and settings
views as stacked pages, plus the (separate) export and raw-data dialogs."""

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from gui.models.settings_model import SettingsModel
from gui.widgets.comparison_widget import ComparisonWidget
from gui.widgets.debug_dialog import DebugDialog
from gui.widgets.export_dialog import ExportDialog
from gui.widgets.settings_view import SettingsView

PAGE_COMPARISON = 0
PAGE_SETTINGS = 1


class MainWindow(QMainWindow):
    """Single-window app. The comparison and settings views are stacked pages;
    this class owns the window, shortcuts, and the export / raw-data dialogs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Syncro Huntress Comparison Tool")
        self.setMinimumSize(900, 600)

        self.settings_model = SettingsModel()
        # When settings are opened because a run was blocked, run once on save.
        self._pending_run = False

        self.comparison_widget = ComparisonWidget(self.settings_model)
        self.settings_view = SettingsView(self.settings_model)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.comparison_widget)  # PAGE_COMPARISON
        self.stack.addWidget(self.settings_view)  # PAGE_SETTINGS
        self.setCentralWidget(self.stack)

        self._connect_signals()
        self._setup_shortcuts()

    def _connect_signals(self):
        cw = self.comparison_widget
        cw.error_occurred.connect(self._show_error)
        cw.settings_requested.connect(self._show_settings)
        cw.export_requested.connect(self._show_export_dialog)
        cw.settings_invalid.connect(self._on_settings_invalid)

        sv = self.settings_view
        sv.saved.connect(self._on_settings_saved)
        sv.cancelled.connect(self._on_settings_cancelled)
        sv.debug_requested.connect(self._show_debug_dialog)

    @Slot(list)
    def _on_settings_invalid(self, errors):
        QMessageBox.warning(
            self,
            "Settings required",
            "Please configure your API settings:\n\n" + "\n".join(errors),
        )
        self._pending_run = True
        self._show_settings()

    def _setup_shortcuts(self):
        export_action = QAction("Export", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._show_export_dialog)
        self.addAction(export_action)

        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        self.addAction(settings_action)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

    @Slot()
    def _show_settings(self):
        self.settings_view.load_values()
        self.stack.setCurrentIndex(PAGE_SETTINGS)

    @Slot()
    def _on_settings_saved(self):
        self.stack.setCurrentIndex(PAGE_COMPARISON)
        if self._pending_run:
            self._pending_run = False
            if self.settings_model.validate()[0]:
                self.comparison_widget.run_comparison()

    @Slot()
    def _on_settings_cancelled(self):
        self._pending_run = False
        self.stack.setCurrentIndex(PAGE_COMPARISON)

    @Slot(str)
    def _show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)

    @Slot()
    def _show_export_dialog(self):
        if not self.comparison_widget.has_results():
            QMessageBox.information(
                self, "No results", "Run a comparison first before exporting."
            )
            return
        dialog = ExportDialog(
            self.comparison_widget.get_results(),
            self.settings_model.get_ignored(),
            self,
        )
        dialog.exec()

    @Slot()
    def _show_debug_dialog(self):
        dialog = DebugDialog(self.comparison_widget.get_raw_data(), self)
        dialog.exec()
