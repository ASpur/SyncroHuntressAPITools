"""Table model for comparison results."""

from typing import Dict, List, Optional, Set

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QFont, QPixmap

from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
from gui.theme import Theme
from gui.theme.theme import dot_pixmap
from services.comparison import ComparisonRow, row_key

# Column indices (single source of truth for ordering).
COL_ORG = 0
COL_SYNCRO = 1
COL_HUNTRESS = 2
COL_STATUS = 3

# Status -> theme token for the status dot drawn in the Status column.
STATUS_TOKENS = {
    STATUS_OK: "status_ok",
    STATUS_MISSING_HUNTRESS: "status_missing_huntress",
    STATUS_MISSING_SYNCRO: "status_missing_syncro",
}

__all__ = [
    "COL_ORG",
    "COL_SYNCRO",
    "COL_HUNTRESS",
    "COL_STATUS",
    "row_key",
    "ComparisonTableModel",
    "ComparisonFilterProxyModel",
]


class ComparisonTableModel(QAbstractTableModel):
    """Table model for displaying comparison results."""

    HEADERS = ["Organization", "Syncro Asset", "Huntress Asset", "Status"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[ComparisonRow] = []
        self._ignored: Set[str] = set()
        self._dots: Dict[str, QPixmap] = {}
        # Repaint status dots / ignored dimming when the OS theme flips.
        Theme.instance().changed.connect(self._on_theme_changed)

    def _dot_for(self, status: str) -> Optional[QPixmap]:
        """Return a cached, palette-colored status dot (or None)."""
        token = STATUS_TOKENS.get(status)
        if token is None:
            return None
        if status not in self._dots:
            self._dots[status] = dot_pixmap(token)
        return self._dots[status]

    def _on_theme_changed(self):
        self._dots.clear()
        if self._data:
            top = self.index(0, 0)
            bottom = self.index(len(self._data) - 1, self.columnCount() - 1)
            self.dataChanged.emit(top, bottom)

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def _cell(self, row: ComparisonRow, col: int) -> str:
        if col == COL_ORG:
            return row.organization
        if col == COL_SYNCRO:
            return row.syncro_name
        if col == COL_HUNTRESS:
            return row.huntress_name
        return row.status

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        row = self._data[index.row()]
        ignored = row_key(row) in self._ignored

        if role == Qt.DisplayRole:
            return self._cell(row, index.column())

        if role == Qt.DecorationRole and index.column() == COL_STATUS and not ignored:
            return self._dot_for(row.status)

        if role == Qt.ForegroundRole and ignored:
            # Dim ignored rows; normal rows inherit the palette text color.
            return Theme.instance().color("ignored_fg")

        if role == Qt.FontRole and ignored:
            font = QFont()
            font.setStrikeOut(True)
            font.setItalic(True)
            return font

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def setData(self, rows: List[ComparisonRow]):
        """Replace all data."""
        self.beginResetModel()
        self._data = list(rows)
        self.endResetModel()

    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._data = []
        self.endResetModel()

    def get_all_data(self) -> List[ComparisonRow]:
        """Get all data rows."""
        return self._data.copy()

    # --- Ignore support ---

    def set_ignored(self, keys: Set[str]):
        """Set the ignored-key set and refresh the view."""
        self._ignored = set(keys)
        if self._data:
            top = self.index(0, 0)
            bottom = self.index(len(self._data) - 1, self.columnCount() - 1)
            self.dataChanged.emit(top, bottom)

    def key_for_source_row(self, source_row: int) -> Optional[str]:
        """Return the ignore key for a source-model row index."""
        if 0 <= source_row < len(self._data):
            return row_key(self._data[source_row])
        return None

    def is_source_row_ignored(self, source_row: int) -> bool:
        key = self.key_for_source_row(source_row)
        return key is not None and key in self._ignored

    def org_for_source_row(self, source_row: int) -> str:
        """Return the organization for a source-model row index."""
        if 0 <= source_row < len(self._data):
            return self._data[source_row].organization
        return ""


class ComparisonFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering comparison results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._statuses: Set[str] = set()  # Empty means show every status
        self._search_text = ""
        self._excluded_orgs: Set[str] = set()
        self._only_ignored = False

    def set_status_filter(self, statuses):
        """Show only rows whose status is in ``statuses`` (an iterable of status
        strings). An empty set shows every status."""
        self._statuses = set(statuses)
        self.invalidateFilter()

    def set_only_ignored(self, only_ignored: bool):
        """When True, show only ignored rows (for the low-weight Ignored view)."""
        self._only_ignored = only_ignored
        self.invalidateFilter()

    def set_search_text(self, text: str):
        """Set the search text filter."""
        self._search_text = text.lower()
        self.invalidateFilter()

    def set_excluded_orgs(self, orgs: Set[str]):
        """Set the organizations to hide."""
        self._excluded_orgs = set(orgs)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()

        def cell(col: int) -> str:
            return model.index(source_row, col, source_parent).data() or ""

        org = cell(COL_ORG)
        syncro = cell(COL_SYNCRO)
        huntress = cell(COL_HUNTRESS)
        status = cell(COL_STATUS)

        # Hide excluded organizations
        if org in self._excluded_orgs:
            return False

        # Ignored-only view overrides the status filter.
        if self._only_ignored:
            if not model.is_source_row_ignored(source_row):
                return False

        # Check status filter (union of selected statuses; empty = show all).
        if self._statuses and status not in self._statuses:
            return False

        # Check search text (org, syncro and huntress names)
        if self._search_text:
            combined = f"{org} {syncro} {huntress}".lower()
            if self._search_text not in combined:
                return False

        return True
