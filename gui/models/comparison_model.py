"""Table model for comparison results."""

from typing import List, Tuple

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor


class ComparisonTableModel(QAbstractTableModel):
    """Table model for displaying comparison results."""

    HEADERS = ["Syncro Asset", "Huntress Asset", "Status"]
    STATUS_BACKGROUNDS = {
        "OK!": QColor(200, 240, 200),  # Green background
        "Missing in Huntress": QColor(255, 200, 200),  # Red background
        "Missing in Syncro": QColor(255, 200, 200),  # Red background
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Tuple[str, str, str]] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            return row[col]

        if role == Qt.BackgroundRole:
            status = row[2]
            return self.STATUS_BACKGROUNDS.get(status)

        if role == Qt.ForegroundRole:
            return QColor(0, 0, 0)  # Black text

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def setData(self, rows: List[Tuple[str, str, str]]):
        """Replace all data."""
        self.beginResetModel()
        self._data = rows
        self.endResetModel()

    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._data = []
        self.endResetModel()

    def get_all_data(self) -> List[Tuple[str, str, str]]:
        """Get all data rows."""
        return self._data.copy()


class ComparisonFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering comparison results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_filter = ""  # Empty means all
        self._search_text = ""

    def set_status_filter(self, status: str):
        """Set the status filter (empty string for all, 'Not OK' for issues only)."""
        self._status_filter = status
        self.invalidateFilter()

    def set_search_text(self, text: str):
        """Set the search text filter."""
        self._search_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()

        # Get row data
        syncro = model.index(source_row, 0, source_parent).data() or ""
        huntress = model.index(source_row, 1, source_parent).data() or ""
        status = model.index(source_row, 2, source_parent).data() or ""

        # Check status filter
        if self._status_filter:
            if self._status_filter == "Not OK":
                if status == "OK!":
                    return False
            elif status != self._status_filter:
                return False

        # Check search text
        if self._search_text:
            combined = f"{syncro} {huntress}".lower()
            if self._search_text not in combined:
                return False

        return True
