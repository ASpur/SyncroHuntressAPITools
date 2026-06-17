"""In-window settings view for API credentials and options.

Lives as a page in the main window's stack (not a modal dialog). Emits ``saved``
or ``cancelled`` so the window can return to the comparison view, and
``debug_requested`` to open the raw-data viewer.
"""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.models.settings_model import SettingsModel


class SuffixLineEdit(QLineEdit):
    """A line edit with a static, greyed suffix pinned inside its right edge
    (e.g. the fixed ``.syncromsp.com`` domain). Typed text is kept clear of the
    suffix via a reserved right text margin."""

    _GAP = 7  # matches the QLineEdit horizontal padding in the QSS

    def __init__(self, suffix: str, parent=None):
        super().__init__(parent)
        self._suffix = QLabel(suffix, self)
        self._suffix.setProperty("role", "hint")
        self._suffix.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._reposition()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()

    def _reposition(self):
        self._suffix.adjustSize()
        reserved = self._suffix.width() + self._GAP
        self.setTextMargins(0, 0, reserved, 0)
        x = self.width() - self._suffix.width() - self._GAP
        y = (self.height() - self._suffix.height()) // 2
        self._suffix.move(max(self._GAP, x), y)


def _key_row(line_edit: QLineEdit) -> QHBoxLayout:
    """Wrap a password field with a Show/Hide reveal toggle."""
    line_edit.setEchoMode(QLineEdit.Password)
    row = QHBoxLayout()
    row.addWidget(line_edit)
    toggle = QPushButton("Show")
    toggle.setCheckable(True)
    toggle.toggled.connect(
        lambda shown: line_edit.setEchoMode(
            QLineEdit.Normal if shown else QLineEdit.Password
        )
    )
    toggle.toggled.connect(lambda shown: toggle.setText("Hide" if shown else "Show"))
    row.addWidget(toggle)
    return row


class SettingsView(QWidget):
    """Edit and persist API settings as an in-window page."""

    saved = Signal()
    cancelled = Signal()
    debug_requested = Signal()

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self._setup_ui()
        self.load_values()

    @staticmethod
    def _section_header(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setProperty("role", "sectionHeader")
        return label

    def _setup_ui(self):
        outer = QVBoxLayout(self)

        # Centered, width-constrained content column.
        content = QWidget()
        content.setMaximumWidth(480)
        col = QVBoxLayout(content)
        col.setSpacing(14)

        title = QLabel("Settings")
        title.setProperty("role", "heroTitle")
        col.addWidget(title)

        # Syncro
        col.addWidget(self._section_header("Syncro MSP"))
        syncro_form = QFormLayout()
        self.syncro_subdomain = SuffixLineEdit(".syncromsp.com")
        self.syncro_subdomain.setPlaceholderText("your-company")
        self.syncro_subdomain.setMinimumWidth(260)
        syncro_form.addRow("Subdomain:", self.syncro_subdomain)
        self.syncro_api_key = QLineEdit()
        self.syncro_api_key.setPlaceholderText("Enter Syncro API key")
        syncro_form.addRow("API key:", _key_row(self.syncro_api_key))
        col.addLayout(syncro_form)

        # Huntress
        col.addWidget(self._section_header("Huntress"))
        huntress_form = QFormLayout()
        self.huntress_api_key = QLineEdit()
        self.huntress_api_key.setPlaceholderText("Enter Huntress API key")
        huntress_form.addRow("API key:", _key_row(self.huntress_api_key))
        self.huntress_secret = QLineEdit()
        self.huntress_secret.setPlaceholderText("Enter Huntress secret key")
        huntress_form.addRow("Secret key:", _key_row(self.huntress_secret))
        col.addLayout(huntress_form)

        # Options
        col.addWidget(self._section_header("Options"))
        self.debug_checkbox = QCheckBox("Enable debug mode (saves raw API responses)")
        col.addWidget(self.debug_checkbox)
        debug_row = QHBoxLayout()
        self.debug_btn = QPushButton("View raw data…")
        self.debug_btn.setToolTip("Inspect the raw API payloads from the last run")
        self.debug_btn.clicked.connect(self.debug_requested)
        debug_row.addWidget(self.debug_btn)
        debug_row.addStretch()
        col.addLayout(debug_row)

        # Inline validation message
        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        col.addWidget(self.error_label)

        col.addStretch()

        # Cancel / Save
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        buttons.addWidget(self.cancel_btn)
        self.save_btn = QPushButton("Save")
        self.save_btn.setProperty("variant", "primary")
        self.save_btn.clicked.connect(self._on_save)
        buttons.addWidget(self.save_btn)
        col.addLayout(buttons)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(content)
        row.addStretch()
        outer.addLayout(row)

    def load_values(self):
        """(Re)populate the fields from the model and clear any error."""
        self.syncro_subdomain.setText(self.settings_model.get("SyncroSubDomain", ""))
        self.syncro_api_key.setText(self.settings_model.get("SyncroAPIKey", ""))
        self.huntress_api_key.setText(self.settings_model.get("HuntressAPIKey", ""))
        self.huntress_secret.setText(self.settings_model.get("HuntressSecretKey", ""))
        self.debug_checkbox.setChecked(self.settings_model.get("Debug", False))
        self.error_label.setVisible(False)

    @Slot()
    def _on_cancel(self):
        self.load_values()
        self.cancelled.emit()

    @Slot()
    def _on_save(self):
        """Validate the form; persist and emit ``saved`` only when valid."""
        values = {
            "SyncroSubDomain": self.syncro_subdomain.text().strip(),
            "SyncroAPIKey": self.syncro_api_key.text().strip(),
            "HuntressAPIKey": self.huntress_api_key.text().strip(),
            "HuntressSecretKey": self.huntress_secret.text().strip(),
        }
        missing = [key for key, value in values.items() if not value]
        if missing:
            self.error_label.setText(
                "All credential fields are required: " + ", ".join(missing)
            )
            self.error_label.setVisible(True)
            return

        for key, value in values.items():
            self.settings_model.set(key, value)
        self.settings_model.set("Debug", self.debug_checkbox.isChecked())

        if not self.settings_model.save():
            self.error_label.setText("Failed to save settings to disk.")
            self.error_label.setVisible(True)
            return

        self.error_label.setVisible(False)
        self.saved.emit()
