"""Export dialog for saving comparison results."""

from typing import List, Tuple

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from utils.output import write_ascii_table, write_csv


class ExportDialog(QDialog):
    """Dialog for exporting comparison results to file."""

    def __init__(self, results: List[Tuple[str, str, str]], parent=None):
        super().__init__(parent)
        self.results = results
        self.setWindowTitle("Export Results")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)

        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "ASCII Table"])
        format_layout.addRow("Format:", self.format_combo)

        layout.addWidget(format_group)

        # File path
        file_group = QGroupBox("Output File")
        file_layout = QHBoxLayout(file_group)

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Select output file...")
        file_layout.addWidget(self.file_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        layout.addWidget(file_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.only_issues_checkbox = QCheckBox("Export only mismatches (exclude OK)")
        options_layout.addWidget(self.only_issues_checkbox)

        layout.addWidget(options_group)

        # Summary
        total = len(self.results)
        issues = sum(1 for r in self.results if r[2] != "OK!")
        self.summary_label = QPushButton(
            f"Ready to export {total} rows ({issues} issues)"
        )
        self.summary_label.setEnabled(False)
        self.summary_label.setFlat(True)
        layout.addWidget(self.summary_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export)
        button_layout.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    @Slot()
    def _browse_file(self):
        """Open file browser dialog."""
        format_text = self.format_combo.currentText()
        if format_text == "CSV":
            filter_str = "CSV Files (*.csv);;All Files (*)"
            default_ext = ".csv"
        else:
            filter_str = "Text Files (*.txt);;All Files (*)"
            default_ext = ".txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Export File", "", filter_str
        )

        if file_path:
            # Ensure correct extension
            if not file_path.endswith(default_ext):
                file_path += default_ext
            self.file_edit.setText(file_path)

    @Slot()
    def _export(self):
        """Perform the export."""
        file_path = self.file_edit.text().strip()

        if not file_path:
            QMessageBox.warning(self, "Error", "Please select an output file.")
            return

        # Filter results if needed
        results = self.results
        if self.only_issues_checkbox.isChecked():
            results = [r for r in results if r[2] != "OK!"]

        if not results:
            QMessageBox.warning(
                self, "Error", "No data to export with current filter settings."
            )
            return

        try:
            format_text = self.format_combo.currentText()
            if format_text == "CSV":
                write_csv(file_path, results)
            else:
                write_ascii_table(file_path, results)

            QMessageBox.information(
                self,
                "Success",
                f"Exported {len(results)} rows to:\n{file_path}",
            )
            self.accept()

        except IOError as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
