"""Main comparison view: top bar, stat-card filters, table, status strip."""

from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
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
from gui.theme.theme import Theme, dot_pixmap
from gui.widgets.org_filter_dialog import OrgFilterDialog
from gui.widgets.spinner import Spinner
from gui.widgets.stat_card import StatCard
from gui.workers.comparison_worker import ComparisonWorker
from services.comparison import ComparisonRow

# Stacked-widget page indices.
PAGE_EMPTY = 0
PAGE_RESULTS = 1

# Status stat-card key -> the status string it selects. These cards multi-select:
# the table shows the union of the selected statuses. "Total" is not in here — it
# clears the selection (shows everything).
STATUS_CARD_KEYS: Dict[str, str] = {
    "ok": STATUS_OK,
    "missing_huntress": STATUS_MISSING_HUNTRESS,
    "missing_syncro": STATUS_MISSING_SYNCRO,
}

# Human labels for the status strip, in display order.
FILTER_LABELS: Dict[str, str] = {
    "ok": "OK",
    "missing_huntress": "missing in Huntress",
    "missing_syncro": "missing in Syncro",
}

# Default view: surface problems first (both "missing" statuses selected).
DEFAULT_SELECTION = frozenset({"missing_huntress", "missing_syncro"})


class ComparisonWidget(QWidget):
    """Displays and manages agent comparisons."""

    comparison_started = Signal()
    comparison_finished = Signal()
    progress_updated = Signal(str)
    error_occurred = Signal(str)
    raw_data_received = Signal(dict)
    # Chrome actions handled by the main window.
    settings_requested = Signal()
    settings_invalid = Signal(list)
    export_requested = Signal()

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self._worker: Optional[ComparisonWorker] = None
        self._all_orgs: List[str] = []
        self._raw_data: dict = {}
        self._cards: Dict[str, StatCard] = {}
        # Selected status-card keys (union filter); empty == show all (Total).
        self._selected: set = set(DEFAULT_SELECTION)
        self._only_ignored = False
        self._ignored_count = 0
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
        """Status hero: a value-prop headline, live connection pills for each
        platform, and the primary Run action. The pills surface setup readiness
        before the user clicks Run, and refresh on settings/theme changes."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.addStretch()

        content = QWidget()
        content.setMaximumWidth(440)
        col = QVBoxLayout(content)
        col.setSpacing(16)
        col.setAlignment(Qt.AlignCenter)

        mark = QFrame()
        mark.setProperty("role", "heroMark")
        mark.setFixedSize(52, 52)
        mark_layout = QVBoxLayout(mark)
        mark_layout.setContentsMargins(0, 0, 0, 0)
        glyph = QLabel("⇄")
        glyph.setAlignment(Qt.AlignCenter)
        glyph.setProperty("role", "heroGlyph")
        mark_layout.addWidget(glyph)
        col.addWidget(mark, alignment=Qt.AlignCenter)

        title = QLabel("Find the gaps between platforms")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("role", "heroTitle")
        col.addWidget(title)

        self._empty_subtitle_default = (
            "Compare Syncro assets against Huntress agents to spot machines "
            "missing from either side."
        )
        self.empty_subtitle = QLabel(self._empty_subtitle_default)
        self.empty_subtitle.setAlignment(Qt.AlignCenter)
        self.empty_subtitle.setWordWrap(True)
        self.empty_subtitle.setProperty("role", "hint")
        col.addWidget(self.empty_subtitle)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(10)
        pills_row.addStretch()
        self._syncro_pill = self._make_status_pill()
        self._huntress_pill = self._make_status_pill()
        pills_row.addWidget(self._syncro_pill[0])
        pills_row.addWidget(self._huntress_pill[0])
        pills_row.addStretch()
        col.addLayout(pills_row)

        self.run_btn_big = QPushButton("Run comparison")
        self.run_btn_big.setProperty("variant", "primary")
        self.run_btn_big.setMinimumSize(220, 48)
        self.run_btn_big.clicked.connect(self.run_comparison)
        col.addWidget(self.run_btn_big, alignment=Qt.AlignCenter)

        # Busy indicator shown in the button's place while a comparison runs.
        self._empty_busy = QFrame()
        self._empty_busy.setProperty("role", "busyButton")
        self._empty_busy.setMinimumSize(220, 48)
        busy_layout = QHBoxLayout(self._empty_busy)
        busy_layout.setContentsMargins(26, 0, 26, 0)
        busy_layout.setSpacing(10)
        busy_layout.addStretch()
        self._empty_spinner = Spinner(16)
        busy_layout.addWidget(self._empty_spinner)
        busy_label = QLabel("Running…")
        busy_label.setProperty("role", "busyLabel")
        busy_layout.addWidget(busy_label)
        busy_layout.addStretch()
        self._empty_busy.setVisible(False)
        col.addWidget(self._empty_busy, alignment=Qt.AlignCenter)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.settings_requested)
        col.addWidget(settings_btn, alignment=Qt.AlignCenter)

        center = QHBoxLayout()
        center.addStretch()
        center.addWidget(content)
        center.addStretch()
        outer.addLayout(center)

        outer.addStretch()

        Theme.instance().changed.connect(self._refresh_connection_status)
        self.settings_model.settings_changed.connect(self._refresh_connection_status)
        self._refresh_connection_status()
        return page

    def _make_status_pill(self) -> tuple:
        """Build a connection pill. Returns ``(frame, dot_label, text_label)``;
        the dot pixmap and text are filled in by ``_refresh_connection_status``."""
        pill = QFrame()
        pill.setProperty("role", "pill")
        layout = QHBoxLayout(pill)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(7)
        dot = QLabel()
        text = QLabel()
        layout.addWidget(dot)
        layout.addWidget(text)
        return pill, dot, text

    @Slot()
    def _refresh_connection_status(self):
        """Repaint both pills from current credentials. Green dot = configured,
        amber dot = needs API keys (mirrors the table's status-dot scheme)."""
        s = self.settings_model
        syncro_ok = bool(
            (s.get("SyncroAPIKey") or "").strip()
            and (s.get("SyncroSubDomain") or "").strip()
        )
        huntress_ok = bool(
            (s.get("HuntressAPIKey") or "").strip()
            and (s.get("HuntressSecretKey") or "").strip()
        )
        self._set_pill(self._syncro_pill, "Syncro", syncro_ok)
        self._set_pill(self._huntress_pill, "Huntress", huntress_ok)

    @staticmethod
    def _set_pill(pill: tuple, name: str, ok: bool):
        _, dot, text = pill
        token = "status_ok" if ok else "status_missing_syncro"
        dot.setPixmap(dot_pixmap(token))
        text.setText(f"{name} connected" if ok else f"{name} — add API keys")

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

        self.rerun_btn = QPushButton("Rerun")
        self.rerun_btn.setProperty("variant", "primary")
        self.rerun_btn.clicked.connect(self.run_comparison)
        bar.addWidget(self.rerun_btn)

        return bar

    def _build_stat_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        specs = [
            ("total", "Total", None),
            ("ok", "OK", "status_ok"),
            ("missing_huntress", "Missing in Huntress", "status_missing_huntress"),
            ("missing_syncro", "Missing in Syncro", "status_missing_syncro"),
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

        # Low-weight ignored entry point: a quiet link that toggles the
        # ignored-only view. Hidden when nothing is ignored.
        self.ignored_btn = QToolButton()
        self.ignored_btn.setProperty("variant", "link")
        self.ignored_btn.setCursor(Qt.PointingHandCursor)
        self.ignored_btn.setVisible(False)
        self.ignored_btn.clicked.connect(self._toggle_ignored_view)
        strip.addWidget(self.ignored_btn)

        export_btn = QToolButton()
        export_btn.setText("Export")
        export_btn.clicked.connect(self.export_requested)
        strip.addWidget(export_btn)
        return strip

    def _set_running(self, running: bool):
        self.progress_bar.setVisible(running)
        self._set_empty_busy(running)

    def _set_empty_busy(self, running: bool):
        """Swap the hero's Run button for an animated busy indicator. The
        subtitle doubles as the live progress line while running."""
        self.run_btn_big.setVisible(not running)
        self._empty_busy.setVisible(running)
        if running:
            self._empty_spinner.start()
            self.empty_subtitle.setText("Starting…")
        else:
            self._empty_spinner.stop()
            self.empty_subtitle.setText(self._empty_subtitle_default)

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
        self.empty_subtitle.setText(message)
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
        self._reset_filter()
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
        """Total clears the selection (show all); the status cards toggle, and
        the table shows the union of whatever is selected."""
        self._only_ignored = False
        if key == "total":
            self._selected = set()
        else:
            self._selected ^= {key}  # toggle membership
        self._apply_selection()

    @Slot()
    def _toggle_ignored_view(self):
        """Flip the quiet ignored link between the ignored-only view and the
        previous status selection."""
        if self._only_ignored:
            self._only_ignored = False
        else:
            self._only_ignored = True
        self._apply_selection()

    def _reset_filter(self):
        """Return to the problems-first default view."""
        self._selected = set(DEFAULT_SELECTION)
        self._only_ignored = False
        self._apply_selection()

    def _apply_selection(self):
        """Push the current selection to the proxy and sync card/link highlights."""
        statuses = {STATUS_CARD_KEYS[k] for k in self._selected}
        self.proxy_model.set_status_filter(statuses)
        self.proxy_model.set_only_ignored(self._only_ignored)

        # Total is "active" when showing everything (no status filter, not ignored).
        self._cards["total"].set_active(not self._only_ignored and not self._selected)
        for key in STATUS_CARD_KEYS:
            self._cards[key].set_active(
                not self._only_ignored and key in self._selected
            )
        self._set_link_active(self.ignored_btn, self._only_ignored)
        self._update_strip()

    @staticmethod
    def _set_link_active(btn: QToolButton, active: bool):
        """Toggle a link button's ``active`` property and re-polish so the QSS
        ``[active="true"]`` rule takes effect."""
        if btn.property("active") == active:
            return
        btn.setProperty("active", active)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

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
            "total": len(active),
            "ok": sum(1 for r in active if r.status == STATUS_OK),
            "missing_huntress": sum(
                1 for r in active if r.status == STATUS_MISSING_HUNTRESS
            ),
            "missing_syncro": sum(
                1 for r in active if r.status == STATUS_MISSING_SYNCRO
            ),
        }
        for key, card in self._cards.items():
            card.set_count(counts[key])
        self._update_ignored_toggle(len(rows) - len(active))

    def _update_ignored_toggle(self, count: int):
        """Refresh the quiet ignored link. Hidden when nothing is ignored; if the
        ignored view is open when the last ignored row clears, fall back home."""
        self._ignored_count = count
        if count == 0:
            self.ignored_btn.setVisible(False)
            if self._only_ignored:
                self._reset_filter()
            return
        self.ignored_btn.setVisible(True)
        self.ignored_btn.setText(f"{count} ignored")

    def _selection_label(self) -> str:
        if self._only_ignored:
            return "ignored"
        if not self._selected:
            return "all"
        if self._selected == set(DEFAULT_SELECTION):
            return "issues"
        return ", ".join(
            label for key, label in FILTER_LABELS.items() if key in self._selected
        )

    def _update_strip(self):
        visible = self.proxy_model.rowCount()
        total = self.model.rowCount()
        self.strip_label.setText(
            f"Showing {visible} of {total} — {self._selection_label()}"
        )

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
