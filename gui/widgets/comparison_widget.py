"""Main comparison view: top bar, stat-card filters, table, status strip."""

from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
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
from gui.widgets.stat_card import StatCard
from gui.workers.comparison_worker import ComparisonWorker
from services.comparison import ComparisonRow

# Stacked-widget page indices.
PAGE_EMPTY = 0
PAGE_RESULTS = 1

# Default filter: surface problems first. Not a stat card, so no card highlights.
DEFAULT_FILTER = "issues"

# filter key -> (proxy status filter, ignored-only, status-strip label)
FILTERS: Dict[str, tuple] = {
    "issues": ("Not OK", False, "issues"),
    "all": ("", False, "all"),
    "ok": (STATUS_OK, False, "OK"),
    "missing_huntress": (STATUS_MISSING_HUNTRESS, False, "missing in Huntress"),
    "missing_syncro": (STATUS_MISSING_SYNCRO, False, "missing in Syncro"),
    "ignored": ("", True, "ignored"),
}


class ComparisonWidget(QWidget):
    """Displays and manages agent comparisons."""

    comparison_started = Signal()
    comparison_finished = Signal()
    progress_updated = Signal(str)
    error_occurred = Signal(str)
    raw_data_received = Signal(dict)
    # Chrome actions handled by the main window (dialogs / about / clear).
    settings_requested = Signal()
    settings_invalid = Signal(list)
    export_requested = Signal()
    clear_requested = Signal()
    debug_requested = Signal()
    about_requested = Signal()

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self._worker: Optional[ComparisonWorker] = None
        self._all_orgs: List[str] = []
        self._raw_data: dict = {}
        self._cards: Dict[str, StatCard] = {}
        self._active_filter = DEFAULT_FILTER
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_results_page())
        self.stack.setCurrentIndex(PAGE_EMPTY)

    # ----- Empty state -----

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        self.run_btn_big = QPushButton("Run Comparison")
        self.run_btn_big.setProperty("variant", "primary")
        self.run_btn_big.setMinimumSize(240, 56)
        self.run_btn_big.clicked.connect(self.run_comparison)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.run_btn_big)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        hint = QLabel("Compare Syncro assets against Huntress agents to find gaps.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setProperty("role", "hint")
        layout.addWidget(hint)

        settings_row = QHBoxLayout()
        settings_row.addStretch()
        settings_btn = QPushButton("Open settings")
        settings_btn.clicked.connect(self.settings_requested)
        settings_row.addWidget(settings_btn)
        settings_row.addStretch()
        layout.addLayout(settings_row)

        layout.addStretch()
        return page

    # ----- Results state -----

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addLayout(self._build_top_bar())
        layout.addLayout(self._build_stat_cards())
        layout.addWidget(self._build_table())
        layout.addLayout(self._build_status_strip())
        return page

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        title = QLabel("Syncro · Huntress")
        bar.addWidget(title)
        self.last_run_label = QLabel("")
        self.last_run_label.setProperty("role", "hint")
        bar.addWidget(self.last_run_label)

        bar.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(220)
        self.search_edit.textChanged.connect(self._on_search_changed)
        bar.addWidget(self.search_edit)

        self.org_btn = QToolButton()
        self.org_btn.setText("All orgs")
        self.org_btn.setToolTip("Choose which organizations are shown")
        self.org_btn.clicked.connect(self._open_org_filter)
        bar.addWidget(self.org_btn)

        gear_btn = QToolButton()
        gear_btn.setText("⚙")
        gear_btn.setToolTip("Settings")
        gear_btn.clicked.connect(self.settings_requested)
        bar.addWidget(gear_btn)

        overflow_btn = QToolButton()
        overflow_btn.setText("⋯")
        overflow_btn.setToolTip("More")
        overflow_btn.setPopupMode(QToolButton.InstantPopup)
        overflow_btn.setMenu(self._build_overflow_menu())
        bar.addWidget(overflow_btn)

        self.rerun_btn = QPushButton("Rerun")
        self.rerun_btn.setProperty("variant", "primary")
        self.rerun_btn.clicked.connect(self.run_comparison)
        bar.addWidget(self.rerun_btn)

        return bar

    def _build_overflow_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("Export results…", self.export_requested.emit)
        menu.addAction("Clear results", self.clear_requested.emit)
        menu.addSeparator()
        menu.addAction("Debug data…", self.debug_requested.emit)
        menu.addAction("About", self.about_requested.emit)
        return menu

    def _build_stat_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        specs = [
            ("all", "Total", None),
            ("ok", "OK", "status_ok"),
            ("missing_huntress", "Missing in Huntress", "status_missing_huntress"),
            ("missing_syncro", "Missing in Syncro", "status_missing_syncro"),
            ("ignored", "Ignored", None),
        ]
        for key, label, dot in specs:
            card = StatCard(key, label, dot)
            card.clicked.connect(self._on_card_clicked)
            self._cards[key] = card
            row.addWidget(card)
        return row

    def _build_table(self) -> QTableView:
        self.model = ComparisonTableModel()
        self.proxy_model = ComparisonFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setSortingEnabled(False)  # Preserve custom sort order
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_table_context_menu)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Organization
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Syncro
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Huntress
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Status
        return self.table_view

    def _build_status_strip(self) -> QHBoxLayout:
        strip = QHBoxLayout()
        self.strip_label = QLabel("")
        self.strip_label.setProperty("role", "hint")
        strip.addWidget(self.strip_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setMaximumWidth(140)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        strip.addWidget(self.progress_bar)

        strip.addStretch()
        export_btn = QToolButton()
        export_btn.setText("Export")
        export_btn.clicked.connect(self.export_requested)
        strip.addWidget(export_btn)
        return strip

    def _set_running(self, running: bool):
        self.progress_bar.setVisible(running)

    # ----- Run / worker plumbing -----

    def _set_run_enabled(self, enabled: bool):
        self.run_btn_big.setEnabled(enabled)
        self.rerun_btn.setEnabled(enabled)

    @Slot()
    def run_comparison(self):
        if self._worker is not None and self._worker.isRunning():
            return

        is_valid, errors = self.settings_model.validate()
        if not is_valid:
            self.settings_invalid.emit(errors)
            return

        self._set_run_enabled(False)
        self._set_running(True)
        self.strip_label.setText("Starting…")
        self.comparison_started.emit()

        settings = self.settings_model.get_all()
        self._worker = ComparisonWorker(settings)
        self._worker.progress.connect(self._on_progress)
        self._worker.error.connect(self._on_error)
        self._worker.result.connect(self._on_result)
        self._worker.raw_data.connect(self._on_raw_data)
        self._worker.finished_work.connect(self._on_finished)
        self._worker.start()

    @Slot(str)
    def _on_progress(self, message: str):
        self.strip_label.setText(message)
        self.progress_updated.emit(message)

    @Slot(dict)
    def _on_raw_data(self, data: dict):
        self._raw_data = data
        self.raw_data_received.emit(data)

    @Slot(list)
    def _on_result(self, rows: List[ComparisonRow]):
        self.model.setData(rows)
        self.model.set_ignored(self.settings_model.get_ignored())

        self._all_orgs = sorted({r.organization for r in rows if r.organization})
        self.proxy_model.set_excluded_orgs(self.settings_model.get_excluded_orgs())
        self._update_org_button_label()

        self._update_summary(rows)
        self._apply_filter(DEFAULT_FILTER)
        self.set_last_run(f"last run {datetime.now():%H:%M}")
        self.stack.setCurrentIndex(PAGE_RESULTS)

    @Slot(str)
    def _on_error(self, message: str):
        self._set_run_enabled(True)
        self._set_running(False)
        self.error_occurred.emit(message)

    @Slot()
    def _on_finished(self):
        self._set_run_enabled(True)
        self._set_running(False)
        self.comparison_finished.emit()

    # ----- Filtering -----

    @Slot(str)
    def _on_search_changed(self, text: str):
        self.proxy_model.set_search_text(text)
        self._update_strip()

    @Slot(str)
    def _on_card_clicked(self, key: str):
        self._apply_filter(key)

    def _apply_filter(self, key: str):
        status, only_ignored, _ = FILTERS[key]
        self.proxy_model.set_status_filter(status)
        self.proxy_model.set_only_ignored(only_ignored)
        self._active_filter = key
        for card_key, card in self._cards.items():
            card.set_active(card_key == key)
        self._update_strip()

    @Slot()
    def _open_org_filter(self):
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
            self._update_strip()

    def _exclude_org(self, org: str):
        if not org:
            return
        excluded = self.settings_model.get_excluded_orgs()
        if org in excluded:
            return
        excluded.add(org)
        self.settings_model.set_excluded_orgs(excluded)
        self.proxy_model.set_excluded_orgs(excluded)
        self._update_org_button_label()
        self._update_strip()

    def _update_org_button_label(self):
        total = len(self._all_orgs)
        excluded = self.settings_model.get_excluded_orgs() & set(self._all_orgs)
        if total == 0:
            self.org_btn.setText("Organizations")
        elif not excluded:
            self.org_btn.setText("All orgs")
        else:
            self.org_btn.setText(f"{total - len(excluded)} of {total} orgs")

    # ----- Context menu (ignore / exclude org) -----

    @Slot()
    def _on_table_context_menu(self, pos):
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
        ignore_action = menu.addAction("Un-ignore asset" if ignored else "Ignore asset")
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
        if ignore:
            self.settings_model.add_ignored(key)
        else:
            self.settings_model.remove_ignored(key)
        self.model.set_ignored(self.settings_model.get_ignored())
        self._update_summary(self.model.get_all_data())
        self.proxy_model.invalidateFilter()
        self._update_strip()

    # ----- Summary / status strip -----

    def _update_summary(self, rows: List[ComparisonRow]):
        ignored = self.settings_model.get_ignored()
        active = [r for r in rows if row_key(r) not in ignored]

        counts = {
            "all": len(active),
            "ok": sum(1 for r in active if r.status == STATUS_OK),
            "missing_huntress": sum(
                1 for r in active if r.status == STATUS_MISSING_HUNTRESS
            ),
            "missing_syncro": sum(
                1 for r in active if r.status == STATUS_MISSING_SYNCRO
            ),
            "ignored": len(rows) - len(active),
        }
        for key, card in self._cards.items():
            card.set_count(counts[key])

    def _update_strip(self):
        visible = self.proxy_model.rowCount()
        total = self.model.rowCount()
        label = FILTERS[self._active_filter][2]
        self.strip_label.setText(f"Showing {visible} of {total} — {label}")

    def set_last_run(self, text: str):
        self.last_run_label.setText(text)

    # ----- Public API used by MainWindow -----

    def has_results(self) -> bool:
        return self.model.rowCount() > 0

    def get_results(self) -> List[ComparisonRow]:
        return self.model.get_all_data()

    def get_raw_data(self) -> dict:
        return self._raw_data

    def clear_results(self):
        self.model.clear()
        self._all_orgs = []
        self._raw_data = {}
        self._update_org_button_label()
        self._update_summary([])
        self.stack.setCurrentIndex(PAGE_EMPTY)
