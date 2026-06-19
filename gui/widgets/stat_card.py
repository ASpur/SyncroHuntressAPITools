"""Clickable summary stat card that doubles as a status filter."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from gui.theme import Theme
from gui.theme.theme import dot_pixmap


class StatCard(QFrame):
    """A labelled count card. Clicking it emits its key for filtering."""

    clicked = Signal(str)

    def __init__(
        self, key: str, label: str, dot_token: Optional[str] = None, parent=None
    ):
        super().__init__(parent)
        self._key = key
        self._dot_token = dot_token
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("active", False)
        self.setAccessibleName(label)
        self.setAccessibleDescription(
            f"Filter results by {label.lower()} status. Click to toggle."
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)

        self._dot = QLabel()
        if dot_token is not None:
            self._dot.setPixmap(dot_pixmap(dot_token))
        header = QLabel(label)
        header.setProperty("role", "hint")

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)
        if dot_token is not None:
            header_row.addWidget(self._dot)
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)

        self._value = QLabel("0")
        font = self._value.font()
        font.setPointSize(font.pointSize() + 6)
        font.setWeight(font.Weight.Medium)
        self._value.setFont(font)
        layout.addWidget(self._value)

        if key == "total":
            self.setToolTip("Click to show all results")
        else:
            self.setToolTip(f"Click to filter by {label.lower()}")

        Theme.instance().changed.connect(self._refresh_dot)

    @property
    def key(self) -> str:
        return self._key

    def set_count(self, count: int):
        self._value.setText(str(count))

    def set_active(self, active: bool):
        if self.property("active") == active:
            return
        self.setProperty("active", active)
        # Re-run the stylesheet so the [active="..."] rule takes effect.
        self.style().unpolish(self)
        self.style().polish(self)

    def _refresh_dot(self):
        if self._dot_token is not None:
            self._dot.setPixmap(dot_pixmap(self._dot_token))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._key)
        super().mousePressEvent(event)
