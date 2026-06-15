"""Table model for comparison results."""

from typing import List, Optional, Set

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QFont

from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
from services.comparison import ComparisonRow, row_key

# Column indices (single source of truth for ordering).
COL_ORG = 0
COL_SYNCRO = 1
COL_HUNTRESS = 2
COL_STATUS = 3

_IGNORED_FOREGROUND = QColor(150, 150, 150)

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
    STATUS_BACKGROUNDS = {
        STATUS_OK: QColor(200, 240, 200),  # Green background
        STATUS_MISSING_HUNTRESS: QColor(255, 200, 200),  # Red background
        STATUS_MISSING_SYNCRO: QColor(255, 200, 200),  # Red background
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[ComparisonRow] = []
        self._ignored: Set[str] = set()

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

        if role == Qt.BackgroundRole:
            if ignored:
                return None  # Keep ignored rows visually muted, not status-colored
            return self.STATUS_BACKGROUNDS.get(row.status)

        if role == Qt.ForegroundRole:
            return _IGNORED_FOREGROUND if ignored else QColor(0, 0, 0)

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
        self._status_filter = ""  # Empty means all
        self._search_text = ""
        self._excluded_orgs: Set[str] = set()

    def set_status_filter(self, status: str):
        """Set the status filter (empty string for all, 'Not OK' for issues only)."""
        self._status_filter = status
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

        # Check status filter
        if self._status_filter:
            if self._status_filter == "Not OK":
                if status == STATUS_OK:
                    return False
            elif status != self._status_filter:
                return False

        # Check search text (org, syncro and huntress names)
        if self._search_text:
            combined = f"{org} {syncro} {huntress}".lower()
            if self._search_text not in combined:
                return False

        return True
