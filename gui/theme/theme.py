"""Applies the neutral theme as a global QSS stylesheet and tracks OS dark/light.

`Theme` is a lightweight singleton. `apply(app)` paints the app from the palette
matching the current OS color scheme and re-paints live when the OS toggles
appearance, emitting `changed` so palette-driven painters (the table model's
status dots, ignored dimming) can refresh.
"""

import math
from string import Template

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from gui.theme.tokens import Palette, palette_for_scheme

# QSS uses braces for rule blocks, so tokens are `$name` (string.Template), not
# `{name}` — that keeps substitution free of brace collisions.
_QSS_TEMPLATE = Template("""
QWidget {
    background: $bg_primary;
    color: $text_primary;
    font-size: 13px;
}

*:focus-visible {
    outline: 2px solid $accent;
    outline-offset: 2px;
}
QLineEdit:focus-visible {
    outline: none;
    border: 1px solid $accent;
}
QPushButton:focus-visible {
    outline: none;
    border: 2px solid $accent;
}

QMainWindow, QDialog { background: $bg_primary; }

QMenuBar {
    background: $bg_primary;
    color: $text_secondary;
    border-bottom: 1px solid $border;
    padding: 2px 4px;
}
QMenuBar::item { padding: 4px 8px; border-radius: 4px; }
QMenuBar::item:selected { background: $hover; color: $text_primary; }

QLabel { background: transparent; }
QLabel[role="muted"] { color: $text_secondary; }
QLabel[role="hint"] { color: $text_tertiary; }
QLabel[role="error"] { color: $status_missing_huntress; }
QLabel[role="warning"] { color: $status_missing_syncro; }
QLabel[role="heroTitle"] { font-size: 19px; font-weight: 500; color: $text_primary; }
QLabel[role="heroGlyph"] { font-size: 24px; color: $text_secondary; }

QFrame[role="heroMark"] {
    background: $bg_secondary;
    border: 1px solid $border;
    border-radius: 14px;
}
QFrame[role="pill"] {
    background: $bg_secondary;
    border: 1px solid $border;
    border-radius: 12px;
}
QFrame[role="pill"] QLabel { background: transparent; color: $text_secondary; }

QFrame[role="busyButton"] {
    background: $bg_secondary;
    border: 1px solid $border;
    border-radius: 6px;
}
QLabel[role="busyLabel"] {
    background: transparent;
    color: $text_tertiary;
    font-weight: 500;
}

Spinner { background: transparent; }

QPushButton {
    background: transparent;
    color: $text_primary;
    border: 1px solid $border_strong;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton:hover { background: $hover; }
QPushButton:pressed { background: $bg_tertiary; }
QPushButton:disabled { color: $text_tertiary; border-color: $border; }
QPushButton[variant="primary"] {
    background: $primary_bg;
    color: $primary_fg;
    border: none;
    font-weight: 500;
}
QPushButton[variant="primary"]:hover { background: $primary_bg_hover; color: #ffffff; }
QPushButton[variant="primary"]:disabled {
    background: $bg_tertiary;
    color: $text_tertiary;
}

QToolButton {
    background: transparent;
    color: $text_secondary;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 5px 10px;
}
QToolButton:hover { background: $hover; }
QToolButton::menu-indicator { image: none; }
QToolButton[variant="link"] {
    background: transparent;
    color: $text_tertiary;
    border: none;
    padding: 5px 6px;
}
QToolButton[variant="link"]:hover { color: $text_secondary; }
QToolButton[variant="link"][active="true"] { color: $accent; }
QToolButton[variant="disclosure"] {
    background: transparent;
    color: $text_tertiary;
    border: none;
    padding: 4px 2px;
    font-size: 11px;
    font-weight: 600;
}
QToolButton[variant="disclosure"]:hover { color: $text_secondary; }
QToolButton:checked { background: $bg_tertiary; color: $text_primary; }

QFrame[role="selectionBar"] {
    background: $bg_secondary;
    border: 1px solid $border;
    border-radius: 8px;
}

QLineEdit {
    background: $bg_primary;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 5px 9px;
    selection-background-color: $selection_bg;
}
QLineEdit:focus { border: 1px solid $accent; }

QComboBox {
    background: $bg_primary;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 4px 9px;
}
QComboBox:focus { border: 1px solid $accent; }
QComboBox QAbstractItemView {
    background: $bg_primary;
    border: 1px solid $border_strong;
    selection-background-color: $selection_bg;
    selection-color: $text_primary;
}

QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $border_strong;
    border-radius: 4px;
    background: $bg_primary;
}
QCheckBox::indicator:hover { border-color: $accent; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; }
QCheckBox::indicator:disabled { border-color: $border; background: $bg_secondary; }

QLabel[role="sectionHeader"] {
    color: $text_secondary;
    font-size: 11px;
    font-weight: 600;
}

QFrame[role="separator"] {
    background: $border;
    max-height: 1px;
}

QTableView {
    background: $bg_primary;
    alternate-background-color: $bg_secondary;
    gridline-color: $border;
    border: 1px solid $border;
    border-radius: 8px;
    selection-background-color: $selection_bg;
    selection-color: $text_primary;
}
QTableView::item { padding: 6px 8px; }
QHeaderView::section {
    background: $bg_secondary;
    color: $text_tertiary;
    border: none;
    border-bottom: 1px solid $border;
    padding: 7px 10px;
}

StatCard {
    background: $bg_primary;
    border: 1px solid $border;
    border-radius: 8px;
}
StatCard:hover { background: $hover; }
StatCard[active="true"] {
    border: 1px solid $accent;
    background: $bg_secondary;
}

QMenu {
    background: $bg_primary;
    border: 1px solid $border_strong;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 22px 6px 14px;
    border-radius: 5px;
}
QMenu::item:selected { background: $hover; }
QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }

QTabWidget::pane { border: 1px solid $border; border-radius: 8px; }
QTabBar::tab {
    background: transparent;
    color: $text_secondary;
    padding: 7px 14px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: $text_primary; border-bottom: 2px solid $accent; }

QPlainTextEdit {
    background: $bg_secondary;
    border: 1px solid $border;
    border-radius: 8px;
}

QProgressBar {
    background: $bg_tertiary;
    border: none;
    border-radius: 4px;
    max-height: 6px;
}
QProgressBar::chunk { background: $accent; border-radius: 4px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical {
    background: $border_strong;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: $text_tertiary; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal {
    background: $border_strong;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
""")


def qss(palette: Palette) -> str:
    """Render the stylesheet for a palette. Raises if a token is missing."""
    return _QSS_TEMPLATE.substitute(palette)


def _device_pixel_ratio() -> float:
    app = QApplication.instance()
    return float(app.devicePixelRatio()) if app is not None else 1.0


def icon_pixmap(name: str, size: int = 16, token: str = "text_secondary") -> QPixmap:
    """A small monochrome line icon painted in the active palette's color.

    Icons are drawn as vector strokes (Feather/Lucide style) so they stay crisp
    at any DPI and re-tint automatically with the theme — the same approach as
    ``dot_pixmap`` and the app icon, with no bundled assets. Names: ``search``,
    ``gear``, ``refresh``, ``chevron-down``, ``eye``, ``eye-off``."""
    dpr = _device_pixel_ratio()
    pm = QPixmap(round(size * dpr), round(size * dpr))
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    color = Theme.instance().color(token)
    pen = QPen(color, max(1.4, size / 11.0))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = float(size)

    if name == "search":
        r = 0.26 * s
        cx = cy = 0.42 * s
        p.drawEllipse(QPointF(cx, cy), r, r)
        off = r * 0.7071
        p.drawLine(QPointF(cx + off, cy + off), QPointF(0.82 * s, 0.82 * s))
    elif name == "refresh":
        rect = QRectF(0.16 * s, 0.16 * s, 0.68 * s, 0.68 * s)
        p.drawArc(rect, 70 * 16, 250 * 16)
        # Arrowhead at the open (leading) end of the arc.
        ang = math.radians(70)
        cx = cy = 0.5 * s
        rad = 0.34 * s
        tx = cx + rad * math.cos(ang)
        ty = cy - rad * math.sin(ang)
        a = 0.14 * s
        p.drawLine(QPointF(tx, ty), QPointF(tx - a, ty - a * 0.15))
        p.drawLine(QPointF(tx, ty), QPointF(tx + a * 0.2, ty - a))
    elif name == "gear":
        cx = cy = 0.5 * s
        ring = 0.22 * s
        p.drawEllipse(QPointF(cx, cy), ring, ring)
        p.drawEllipse(QPointF(cx, cy), 0.09 * s, 0.09 * s)
        p.save()
        p.translate(cx, cy)
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        tooth_w = 0.13 * s
        for _ in range(8):
            p.drawRoundedRect(
                QRectF(-tooth_w / 2, -(ring + 0.13 * s), tooth_w, 0.16 * s), 1.0, 1.0
            )
            p.rotate(45)
        p.restore()
    elif name == "chevron-down":
        p.drawLine(QPointF(0.28 * s, 0.40 * s), QPointF(0.5 * s, 0.60 * s))
        p.drawLine(QPointF(0.5 * s, 0.60 * s), QPointF(0.72 * s, 0.40 * s))
    elif name in ("eye", "eye-off"):
        p.drawEllipse(QPointF(0.5 * s, 0.5 * s), 0.32 * s, 0.19 * s)
        p.drawEllipse(QPointF(0.5 * s, 0.5 * s), 0.085 * s, 0.085 * s)
        if name == "eye-off":
            p.drawLine(QPointF(0.20 * s, 0.20 * s), QPointF(0.80 * s, 0.80 * s))

    p.end()
    return pm


def dot_pixmap(token: str, diameter: int = 10) -> QPixmap:
    """A small filled circle in the active palette's color for ``token``."""
    pixmap = QPixmap(diameter, diameter)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(Theme.instance().color(token))
    painter.drawEllipse(1, 1, diameter - 2, diameter - 2)
    painter.end()
    return pixmap


class Theme(QObject):
    """Singleton holding the active palette and applying it as global QSS."""

    changed = Signal()

    _instance = None

    def __init__(self):
        super().__init__()
        self._app = None
        self._palette: Palette = palette_for_scheme(False)

    @classmethod
    def instance(cls) -> "Theme":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def palette(self) -> Palette:
        return self._palette

    def color(self, token: str) -> QColor:
        """QColor for a token, for code that paints (e.g. status dots)."""
        return QColor(self._palette[token])

    def apply(self, app) -> None:
        """Paint the app from the OS scheme and follow live appearance changes."""
        self._app = app
        hints = app.styleHints()
        self._repaint(self._is_dark(hints))
        hints.colorSchemeChanged.connect(self._on_scheme_changed)

    @staticmethod
    def _is_dark(hints) -> bool:
        return hints.colorScheme() == Qt.ColorScheme.Dark

    def _on_scheme_changed(self, scheme) -> None:
        self._repaint(scheme == Qt.ColorScheme.Dark)

    def _repaint(self, is_dark: bool) -> None:
        self._palette = palette_for_scheme(is_dark)
        if self._app is not None:
            self._app.setStyleSheet(qss(self._palette))
        self.changed.emit()
