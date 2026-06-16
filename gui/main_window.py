"""Main application window: hosts the comparison view and orchestrates dialogs."""

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMessageBox

from gui.models.settings_model import SettingsModel
from gui.widgets.comparison_widget import ComparisonWidget
from gui.widgets.debug_dialog import DebugDialog
from gui.widgets.export_dialog import ExportDialog
from gui.widgets.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Single-screen window. Chrome lives in the comparison view; this class
    owns the window, keyboard shortcuts, and the modal dialogs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Syncro Huntress Comparison Tool")
        self.setMinimumSize(900, 600)

        self.settings_model = SettingsModel()

        self.comparison_widget = ComparisonWidget(self.settings_model)
        self.setCentralWidget(self.comparison_widget)

        self._connect_signals()
        self._setup_shortcuts()

    def _connect_signals(self):
        cw = self.comparison_widget
        cw.error_occurred.connect(self._show_error)
        cw.settings_requested.connect(self._show_settings)
        cw.export_requested.connect(self._show_export_dialog)
        cw.clear_requested.connect(self._clear_results)
        cw.debug_requested.connect(self._show_debug_dialog)
        cw.about_requested.connect(self._show_about)
        cw.settings_invalid.connect(self._on_settings_invalid)

    @Slot(list)
    def _on_settings_invalid(self, errors):
        QMessageBox.warning(
            self,
            "Settings required",
            "Please configure your API settings:\n\n" + "\n".join(errors),
        )
        dialog = SettingsDialog(self.settings_model, self)
        if dialog.exec() and self.settings_model.validate()[0]:
            self.comparison_widget.run_comparison()

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
        dialog = SettingsDialog(self.settings_model, self)
        dialog.exec()

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

    @Slot()
    def _clear_results(self):
        self.comparison_widget.clear_results()

    @Slot()
    def _show_about(self):
        QMessageBox.about(
            self,
            "About",
            "Syncro Huntress Comparison Tool\n\n"
            "Compare agents between Syncro and Huntress to identify "
            "missing or mismatched deployments.",
        )
