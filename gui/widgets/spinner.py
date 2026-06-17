"""A small indeterminate spinner: a rotating arc painted from the active palette.

Qt ships no spinner widget, so this draws a faint full ring plus a brighter
90° head arc that advances on a timer. Colors are read from the `Theme`
singleton at paint time, so it follows OS light/dark like the rest of the UI.
The timer only runs between `start()` and `stop()` to avoid idle repaints.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.theme.theme import Theme


class Spinner(QWidget):
    """An indeterminate rotating-arc busy indicator."""

    def __init__(self, diameter: int = 16, parent=None):
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._advance)
        self.hide()

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance(self) -> None:
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        pen = QPen()
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)

        pen.setColor(Theme.instance().color("border_strong"))
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        pen.setColor(Theme.instance().color("text_secondary"))
        painter.setPen(pen)
        start = (90 - self._angle) * 16
        painter.drawArc(rect, start, 90 * 16)
        painter.end()
