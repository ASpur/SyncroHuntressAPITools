"""Main comparison view widget."""

from typing import List, Tuple, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QPushButton,
    QComboBox,
    QLineEdit,
    QLabel,
    QHeaderView,
)
from PySide6.QtCore import Signal, Slot

from gui.models.settings_model import SettingsModel
from gui.models.comparison_model import ComparisonTableModel, ComparisonFilterProxyModel
from gui.workers.comparison_worker import ComparisonWorker


class ComparisonWidget(QWidget):
    """Widget for displaying and managing agent comparisons."""

    comparison_started = Signal()
    comparison_finished = Signal()
    progress_updated = Signal(str)
    error_occurred = Signal(str)
    raw_data_received = Signal(dict)

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self._worker: Optional[ComparisonWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)

        # Controls row
        controls_layout = QHBoxLayout()

        self.compare_btn = QPushButton("Run Comparison")
        self.compare_btn.clicked.connect(self.run_comparison)
        controls_layout.addWidget(self.compare_btn)

        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Not OK", "OK!", "Missing in Huntress", "Missing in Syncro"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        controls_layout.addWidget(self.filter_combo)

        controls_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to search...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        controls_layout.addWidget(self.search_edit)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Table view
        self.model = ComparisonTableModel()
        self.proxy_model = ComparisonFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(False)  # Preserve custom sort order
        self.table_view.setSelectionBehavior(QTableView.SelectRows)

        # Configure column sizing
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        layout.addWidget(self.table_view)

        # Summary row
        summary_layout = QHBoxLayout()

        self.total_label = QLabel("Total: 0")
        summary_layout.addWidget(self.total_label)

        self.ok_label = QLabel("OK: 0")
        self.ok_label.setStyleSheet("color: green;")
        summary_layout.addWidget(self.ok_label)

        self.missing_huntress_label = QLabel("Missing in Huntress: 0")
        self.missing_huntress_label.setStyleSheet("color: red;")
        summary_layout.addWidget(self.missing_huntress_label)

        self.missing_syncro_label = QLabel("Missing in Syncro: 0")
        self.missing_syncro_label.setStyleSheet("color: orange;")
        summary_layout.addWidget(self.missing_syncro_label)

        summary_layout.addStretch()

        layout.addLayout(summary_layout)

    @Slot()
    def run_comparison(self):
        """Start the comparison worker."""
        if self._worker is not None and self._worker.isRunning():
            return

        self.compare_btn.setEnabled(False)
        self.comparison_started.emit()

        settings = self.settings_model.get_all()
        self._worker = ComparisonWorker(settings)
        self._worker.progress.connect(self.progress_updated)
        self._worker.error.connect(self._on_error)
        self._worker.result.connect(self._on_result)
        self._worker.raw_data.connect(self.raw_data_received)
        self._worker.finished_work.connect(self._on_finished)
        self._worker.start()

    @Slot(list)
    def _on_result(self, rows: List[Tuple[str, str, str]]):
        """Handle comparison results."""
        self.model.setData(rows)
        self._update_summary(rows)

    @Slot(str)
    def _on_error(self, message: str):
        """Handle worker error."""
        self.compare_btn.setEnabled(True)
        self.error_occurred.emit(message)

    @Slot()
    def _on_finished(self):
        """Handle worker completion."""
        self.compare_btn.setEnabled(True)
        self.comparison_finished.emit()

    @Slot(str)
    def _on_filter_changed(self, text: str):
        """Handle filter combo change."""
        status = "" if text == "All" else text
        self.proxy_model.set_status_filter(status)

    @Slot(str)
    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self.proxy_model.set_search_text(text)

    def _update_summary(self, rows: List[Tuple[str, str, str]]):
        """Update summary labels."""
        total = len(rows)
        ok_count = sum(1 for r in rows if r[2] == "OK!")
        missing_huntress = sum(1 for r in rows if r[2] == "Missing in Huntress")
        missing_syncro = sum(1 for r in rows if r[2] == "Missing in Syncro")

        self.total_label.setText(f"Total: {total}")
        self.ok_label.setText(f"OK: {ok_count}")
        self.missing_huntress_label.setText(f"Missing in Huntress: {missing_huntress}")
        self.missing_syncro_label.setText(f"Missing in Syncro: {missing_syncro}")

    def has_results(self) -> bool:
        """Check if there are results to export."""
        return self.model.rowCount() > 0

    def get_results(self) -> List[Tuple[str, str, str]]:
        """Get the comparison results."""
        return self.model.get_all_data()

    def clear_results(self):
        """Clear all results."""
        self.model.clear()
        self._update_summary([])
