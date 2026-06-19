"""Export dialog for saving comparison results."""

from typing import List, Optional, Set

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from const import STATUS_OK
from services.comparison import ComparisonRow
from utils.output import write_ascii_table, write_csv


class ExportDialog(QDialog):
    """Dialog for exporting comparison results to file."""

    def __init__(
        self,
        results: List[ComparisonRow],
        ignored_keys: Optional[Set[str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.results = results
        self.ignored_keys = ignored_keys or set()
        self.setWindowTitle("Export Results")
        self.setMinimumWidth(400)
        self._setup_ui()

    @staticmethod
    def _section_header(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setProperty("role", "sectionHeader")
        return label

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Format selection
        layout.addWidget(self._section_header("Export Format"))
        format_form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "ASCII Table"])
        format_form.addRow("Format:", self.format_combo)
        layout.addLayout(format_form)

        # File path
        layout.addWidget(self._section_header("Output File"))
        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Select output file...")
        file_row.addWidget(self.file_edit)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.browse_btn)
        layout.addLayout(file_row)

        # Options
        layout.addWidget(self._section_header("Options"))
        self.only_issues_checkbox = QCheckBox("Export only mismatches (exclude OK)")
        layout.addWidget(self.only_issues_checkbox)

        # Summary
        total = len(self.results)
        issues = sum(1 for r in self.results if r.status != STATUS_OK)
        self.summary_label = QLabel(
            f"Ready to export {total} rows ({issues} issues)"
        )
        self.summary_label.setProperty("role", "hint")
        layout.addWidget(self.summary_label)

        # Buttons — Cancel on left, Export (primary) on right
        self.export_btn = QPushButton("Export")
        self.export_btn.setProperty("variant", "primary")
        self.export_btn.clicked.connect(self._export)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        button_box = QDialogButtonBox()
        button_box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        button_box.addButton(self.export_btn, QDialogButtonBox.AcceptRole)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

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
            results = [r for r in results if r.status != STATUS_OK]

        if not results:
            QMessageBox.warning(
                self, "Error", "No data to export with current filter settings."
            )
            return

        try:
            format_text = self.format_combo.currentText()
            if format_text == "CSV":
                write_csv(file_path, results, self.ignored_keys)
            else:
                write_ascii_table(file_path, results, ignored_keys=self.ignored_keys)

            QMessageBox.information(
                self,
                "Success",
                f"Exported {len(results)} rows to:\n{file_path}",
            )
            self.accept()

        except IOError as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
