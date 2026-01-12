"""Main application window."""

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QTabWidget,
    QToolBar,
)

from gui.models.settings_model import SettingsModel
from gui.widgets.comparison_widget import ComparisonWidget
from gui.widgets.debug_widget import DebugWidget
from gui.widgets.export_dialog import ExportDialog
from gui.widgets.settings_widget import SettingsWidget


class MainWindow(QMainWindow):
    """Main application window with tabs for comparison, settings, and debug."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Syncro Huntress Comparison Tool")
        self.setMinimumSize(900, 600)

        # Initialize settings model
        self.settings_model = SettingsModel()

        # Setup UI components
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

    def _setup_menu_bar(self):
        """Create the menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        export_action = QAction("&Export Results...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        clear_action = QAction("&Clear Results", self)
        clear_action.triggered.connect(self._clear_results)
        view_menu.addAction(clear_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.compare_action = QAction("Compare", self)
        self.compare_action.triggered.connect(self._run_comparison)
        toolbar.addAction(self.compare_action)

        self.export_action = QAction("Export", self)
        self.export_action.triggered.connect(self._show_export_dialog)
        toolbar.addAction(self.export_action)

    def _setup_central_widget(self):
        """Create the central tabbed widget."""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Comparison tab
        self.comparison_widget = ComparisonWidget(self.settings_model)
        self.comparison_widget.comparison_started.connect(self._on_comparison_started)
        self.comparison_widget.comparison_finished.connect(self._on_comparison_finished)
        self.comparison_widget.progress_updated.connect(self._update_status)
        self.comparison_widget.error_occurred.connect(self._show_error)
        self.tabs.addTab(self.comparison_widget, "Comparison")

        # Settings tab
        self.settings_widget = SettingsWidget(self.settings_model)
        self.tabs.addTab(self.settings_widget, "Settings")

        # Debug tab
        self.debug_widget = DebugWidget()
        self.comparison_widget.raw_data_received.connect(self.debug_widget.set_raw_data)
        self.tabs.addTab(self.debug_widget, "Debug")

    def _setup_status_bar(self):
        """Create the status bar with progress indicator."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    @Slot()
    def _run_comparison(self):
        """Trigger the comparison operation."""
        # Validate settings first
        is_valid, errors = self.settings_model.validate()
        if not is_valid:
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please configure your API settings:\n\n" + "\n".join(errors),
            )
            self.tabs.setCurrentIndex(1)  # Switch to settings tab
            return

        self.comparison_widget.run_comparison()

    @Slot()
    def _on_comparison_started(self):
        """Handle comparison start."""
        self.progress_bar.setVisible(True)
        self.compare_action.setEnabled(False)
        self.export_action.setEnabled(False)

    @Slot()
    def _on_comparison_finished(self):
        """Handle comparison completion."""
        self.progress_bar.setVisible(False)
        self.compare_action.setEnabled(True)
        self.export_action.setEnabled(True)
        self.status_label.setText("Ready")

    @Slot(str)
    def _update_status(self, message: str):
        """Update status bar message."""
        self.status_label.setText(message)

    @Slot(str)
    def _show_error(self, message: str):
        """Show error dialog."""
        self.progress_bar.setVisible(False)
        self.compare_action.setEnabled(True)
        self.export_action.setEnabled(True)
        self.status_label.setText("Error occurred")
        QMessageBox.critical(self, "Error", message)

    @Slot()
    def _show_export_dialog(self):
        """Show the export dialog."""
        if not self.comparison_widget.has_results():
            QMessageBox.information(
                self, "No Results", "Run a comparison first before exporting."
            )
            return

        dialog = ExportDialog(self.comparison_widget.get_results(), self)
        dialog.exec()

    @Slot()
    def _clear_results(self):
        """Clear comparison results."""
        self.comparison_widget.clear_results()
        self.debug_widget.clear_data()

    @Slot()
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About",
            "Syncro Huntress Comparison Tool\n\n"
            "Compare agents between Syncro and Huntress to identify "
            "missing or mismatched deployments.",
        )
