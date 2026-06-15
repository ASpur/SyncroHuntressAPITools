"""Dialog for choosing which organizations are shown in the comparison."""

from typing import List, Set

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class OrgFilterDialog(QDialog):
    """Checkable list of organizations. Checked = shown, unchecked = excluded."""

    def __init__(self, organizations: List[str], excluded: Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Organizations")
        self.setMinimumSize(320, 420)
        self._setup_ui(organizations, excluded)

    def _setup_ui(self, organizations: List[str], excluded: Set[str]):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Checked organizations are shown; uncheck to hide."))

        # Search box to filter the (potentially long) org list
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search organizations...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search)
        layout.addWidget(self.search_edit)

        # Select all / none controls
        controls = QHBoxLayout()
        self.check_all_btn = QPushButton("Check All")
        self.check_all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        controls.addWidget(self.check_all_btn)

        self.uncheck_all_btn = QPushButton("Uncheck All")
        self.uncheck_all_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        controls.addWidget(self.uncheck_all_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.list_widget = QListWidget()
        for org in organizations:
            item = QListWidgetItem(org)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if org in excluded else Qt.Checked)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @Slot()
    def _set_all(self, state: Qt.CheckState):
        # Only affect currently-visible (filtered) rows, so a search + "Uncheck
        # All" can toggle just the matching subset.
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(state)

    @Slot(str)
    def _on_search(self, text: str):
        query = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(query not in item.text().lower())

    def excluded_orgs(self) -> Set[str]:
        """Return the set of unchecked (excluded) organization names."""
        excluded = set()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Unchecked:
                excluded.add(item.text())
        return excluded
