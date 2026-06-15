"""Main comparison view widget."""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
from gui.models.comparison_model import (
    ComparisonFilterProxyModel,
    ComparisonTableModel,
    row_key,
)
from gui.models.settings_model import SettingsModel
from gui.widgets.org_filter_dialog import OrgFilterDialog
from gui.workers.comparison_worker import ComparisonWorker
from services.comparison import ComparisonRow

# Stacked-widget page indices.
PAGE_EMPTY = 0
PAGE_RESULTS = 1


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
        self._all_orgs: List[str] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components."""
        outer = QVBoxLayout(self)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_results_page())
        self.stack.setCurrentIndex(PAGE_EMPTY)

    def _build_empty_page(self) -> QWidget:
        """Empty state: a large, centered Run Comparison button."""
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addStretch()

        self.run_btn_big = QPushButton("Run Comparison")
        self.run_btn_big.setMinimumSize(240, 64)
        self.run_btn_big.clicked.connect(self.run_comparison)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.run_btn_big)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        hint = QLabel("Compare Syncro assets against Huntress agents to find gaps.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def _build_results_page(self) -> QWidget:
        """Results state: controls, table and summary."""
        page = QWidget()
        layout = QVBoxLayout(page)

        # Controls row: filters on the left, asset search on the right.
        controls_layout = QHBoxLayout()

        self.rerun_btn = QPushButton("Rerun Comparison")
        self.rerun_btn.clicked.connect(self.run_comparison)
        controls_layout.addWidget(self.rerun_btn)

        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            ["All", "Not OK", STATUS_OK, STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO]
        )
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        controls_layout.addWidget(self.filter_combo)

        self.org_btn = QToolButton()
        self.org_btn.setText("All orgs")
        self.org_btn.setToolTip("Choose which organizations are shown")
        self.org_btn.clicked.connect(self._open_org_filter)
        controls_layout.addWidget(self.org_btn)

        # Push the search box to the right edge.
        controls_layout.addStretch()

        controls_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to search...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(280)
        self.search_edit.textChanged.connect(self._on_search_changed)
        controls_layout.addWidget(self.search_edit)

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
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_table_context_menu)

        # Configure column sizing
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Organization
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Syncro
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Huntress
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Status

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

        self.ignored_label = QLabel("Ignored: 0")
        self.ignored_label.setStyleSheet("color: gray;")
        summary_layout.addWidget(self.ignored_label)

        summary_layout.addStretch()

        layout.addLayout(summary_layout)
        return page

    def _set_run_enabled(self, enabled: bool):
        """Enable/disable both run buttons together."""
        self.run_btn_big.setEnabled(enabled)
        self.rerun_btn.setEnabled(enabled)

    @Slot()
    def run_comparison(self):
        """Start the comparison worker."""
        if self._worker is not None and self._worker.isRunning():
            return

        self._set_run_enabled(False)
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
    def _on_result(self, rows: List[ComparisonRow]):
        """Handle comparison results."""
        self.model.setData(rows)
        self.model.set_ignored(self.settings_model.get_ignored())

        self._all_orgs = sorted({r.organization for r in rows if r.organization})
        self.proxy_model.set_excluded_orgs(self.settings_model.get_excluded_orgs())
        self._update_org_button_label()

        self._update_summary(rows)
        self.stack.setCurrentIndex(PAGE_RESULTS)

    @Slot(str)
    def _on_error(self, message: str):
        """Handle worker error."""
        self._set_run_enabled(True)
        self.error_occurred.emit(message)

    @Slot()
    def _on_finished(self):
        """Handle worker completion."""
        self._set_run_enabled(True)
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

    @Slot()
    def _open_org_filter(self):
        """Open the organization filter dialog."""
        if not self._all_orgs:
            return
        dialog = OrgFilterDialog(
            self._all_orgs, self.settings_model.get_excluded_orgs(), self
        )
        if dialog.exec():
            excluded = dialog.excluded_orgs()
            self.settings_model.set_excluded_orgs(excluded)
            self.proxy_model.set_excluded_orgs(excluded)
            self._update_org_button_label()

    def _exclude_org(self, org: str):
        """Add an organization to the excluded set (from the row context menu)."""
        if not org:
            return
        excluded = self.settings_model.get_excluded_orgs()
        if org in excluded:
            return
        excluded.add(org)
        self.settings_model.set_excluded_orgs(excluded)
        self.proxy_model.set_excluded_orgs(excluded)
        self._update_org_button_label()

    def _update_org_button_label(self):
        """Reflect org-filter state on the toolbar button."""
        total = len(self._all_orgs)
        excluded = self.settings_model.get_excluded_orgs() & set(self._all_orgs)
        if total == 0:
            self.org_btn.setText("Organizations")
        elif not excluded:
            self.org_btn.setText("All orgs")
        else:
            self.org_btn.setText(f"{total - len(excluded)} of {total} orgs")

    @Slot()
    def _on_table_context_menu(self, pos):
        """Show ignore/un-ignore menu for the clicked row."""
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        source_row = self.proxy_model.mapToSource(index).row()
        key = self.model.key_for_source_row(source_row)
        if not key:
            return

        ignored = self.model.is_source_row_ignored(source_row)
        org = self.model.org_for_source_row(source_row)

        menu = QMenu(self)
        ignore_action = menu.addAction(
            "Un-ignore asset" if ignored else "Ignore asset"
        )
        exclude_org_action = None
        if org:
            menu.addSeparator()
            exclude_org_action = menu.addAction(f"Filter out organization “{org}”")

        chosen = menu.exec(self.table_view.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == ignore_action:
            self._toggle_ignore(key, not ignored)
        elif chosen == exclude_org_action:
            self._exclude_org(org)

    def _toggle_ignore(self, key: str, ignore: bool):
        """Persist and apply an ignore-state change."""
        if ignore:
            self.settings_model.add_ignored(key)
        else:
            self.settings_model.remove_ignored(key)
        self.model.set_ignored(self.settings_model.get_ignored())
        self._update_summary(self.model.get_all_data())

    def _update_summary(self, rows: List[ComparisonRow]):
        """Update summary labels (ignored rows excluded from mismatch counts)."""
        ignored = self.settings_model.get_ignored()
        active = [r for r in rows if row_key(r) not in ignored]

        total = len(active)
        ok_count = sum(1 for r in active if r.status == STATUS_OK)
        missing_huntress = sum(1 for r in active if r.status == STATUS_MISSING_HUNTRESS)
        missing_syncro = sum(1 for r in active if r.status == STATUS_MISSING_SYNCRO)
        ignored_count = len(rows) - total

        self.total_label.setText(f"Total: {total}")
        self.ok_label.setText(f"OK: {ok_count}")
        self.missing_huntress_label.setText(f"Missing in Huntress: {missing_huntress}")
        self.missing_syncro_label.setText(f"Missing in Syncro: {missing_syncro}")
        self.ignored_label.setText(f"Ignored: {ignored_count}")

    def has_results(self) -> bool:
        """Check if there are results to export."""
        return self.model.rowCount() > 0

    def get_results(self) -> List[ComparisonRow]:
        """Get the comparison results."""
        return self.model.get_all_data()

    def clear_results(self):
        """Clear all results and return to the empty state."""
        self.model.clear()
        self._all_orgs = []
        self._update_org_button_label()
        self._update_summary([])
        self.stack.setCurrentIndex(PAGE_EMPTY)
