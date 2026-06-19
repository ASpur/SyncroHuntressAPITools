"""In-window settings view for API credentials and options.

Lives as a page in the main window's stack (not a modal dialog). Emits ``saved``
or ``cancelled`` so the window can return to the comparison view, and
``debug_requested`` to open the raw-data viewer.
"""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
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


def _add_password_toggle(line_edit: QLineEdit) -> QLineEdit:
    """Add an inline eye icon action to toggle password visibility."""
    line_edit.setEchoMode(QLineEdit.Password)
    toggle_action = QAction("\U0001f441", line_edit)
    toggle_action.setCheckable(True)
    toggle_action.toggled.connect(
        lambda shown: line_edit.setEchoMode(
            QLineEdit.Normal if shown else QLineEdit.Password
        )
    )
    toggle_action.setToolTip("Show / hide password")
    line_edit.addAction(toggle_action, QLineEdit.TrailingPosition)
    return line_edit


class SettingsView(QWidget):
    """Edit and persist API settings as an in-window page."""

    saved = Signal()
    cancelled = Signal()
    debug_requested = Signal()

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self._dirty = False
        self._setup_ui()
        self._connect_dirty_signals()
        self.load_values()

    @staticmethod
    def _section_header(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setProperty("role", "sectionHeader")
        return label

    def _connect_dirty_signals(self):
        for field in (
            self.syncro_subdomain,
            self.syncro_api_key,
            self.huntress_api_key,
            self.huntress_secret,
        ):
            field.textChanged.connect(self._mark_dirty)
        self.fake_data_checkbox.toggled.connect(self._mark_dirty)
        self.debug_checkbox.toggled.connect(self._mark_dirty)

    def _mark_dirty(self):
        self._dirty = True

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
        syncro_form.addRow("API key:", _add_password_toggle(self.syncro_api_key))
        col.addLayout(syncro_form)

        # Huntress
        col.addWidget(self._section_header("Huntress"))
        huntress_form = QFormLayout()
        self.huntress_api_key = QLineEdit()
        self.huntress_api_key.setPlaceholderText("Enter Huntress API key")
        huntress_form.addRow("API key:", _add_password_toggle(self.huntress_api_key))
        self.huntress_secret = QLineEdit()
        self.huntress_secret.setPlaceholderText("Enter Huntress secret key")
        huntress_form.addRow("Secret key:", _add_password_toggle(self.huntress_secret))
        col.addLayout(huntress_form)

        # Inline validation message
        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        col.addWidget(self.error_label)

        self.warning_label = QLabel("")
        self.warning_label.setProperty("role", "warning")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        col.addWidget(self.warning_label)

        col.addStretch()

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setProperty("role", "separator")
        col.addWidget(separator)

        # Debug (collapsible, closed by default)
        self.debug_toggle = QToolButton()
        self.debug_toggle.setText("Debug")
        self.debug_toggle.setCheckable(True)
        self.debug_toggle.setChecked(False)
        self.debug_toggle.setProperty("variant", "disclosure")
        self.debug_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.debug_toggle.setArrowType(Qt.RightArrow)
        self.debug_toggle.toggled.connect(self._on_debug_toggled)
        col.addWidget(self.debug_toggle)

        self.debug_panel = QWidget()
        debug_layout = QVBoxLayout(self.debug_panel)
        debug_layout.setContentsMargins(16, 6, 0, 0)
        debug_layout.setSpacing(8)
        self.fake_data_checkbox = QCheckBox("Use fake data (test GUI without API keys)")
        self.fake_data_checkbox.setToolTip(
            "Populate the comparison with fake data so you can explore "
            "the GUI without configuring API credentials."
        )
        debug_layout.addWidget(self.fake_data_checkbox)
        self.debug_checkbox = QCheckBox("Enable debug mode (saves raw API responses)")
        debug_layout.addWidget(self.debug_checkbox)
        debug_row = QHBoxLayout()
        self.debug_btn = QPushButton("View raw data…")
        self.debug_btn.setToolTip("Inspect the raw API payloads from the last run")
        self.debug_btn.clicked.connect(self.debug_requested)
        debug_row.addWidget(self.debug_btn)
        debug_row.addStretch()
        debug_layout.addLayout(debug_row)
        self.debug_panel.setVisible(False)
        col.addWidget(self.debug_panel)

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

        self.setTabOrder(self.syncro_subdomain, self.syncro_api_key)
        self.setTabOrder(self.syncro_api_key, self.huntress_api_key)
        self.setTabOrder(self.huntress_api_key, self.huntress_secret)
        self.setTabOrder(self.huntress_secret, self.debug_toggle)
        self.setTabOrder(self.debug_toggle, self.fake_data_checkbox)
        self.setTabOrder(self.fake_data_checkbox, self.debug_checkbox)
        self.setTabOrder(self.debug_checkbox, self.cancel_btn)
        self.setTabOrder(self.cancel_btn, self.save_btn)

    def load_values(self):
        """(Re)populate the fields from the model and clear any error."""
        self.syncro_subdomain.setText(self.settings_model.get("SyncroSubDomain", ""))
        self.syncro_api_key.setText(self.settings_model.get("SyncroAPIKey", ""))
        self.huntress_api_key.setText(self.settings_model.get("HuntressAPIKey", ""))
        self.huntress_secret.setText(self.settings_model.get("HuntressSecretKey", ""))
        self.fake_data_checkbox.setChecked(self.settings_model.get("UseFakeData", False))
        self.debug_checkbox.setChecked(self.settings_model.get("Debug", False))
        self.error_label.setVisible(False)
        self.warning_label.setVisible(False)
        self._dirty = False

    @Slot()
    def _on_cancel(self):
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Discard changes?",
                "You have unsaved changes. Discard them?",
                QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer != QMessageBox.Discard:
                return
        self.load_values()
        self.cancelled.emit()

    @Slot(bool)
    def _on_debug_toggled(self, checked: bool):
        self.debug_panel.setVisible(checked)
        self.debug_toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    @Slot()
    def _on_save(self):
        """Persist settings and emit ``saved``. Shows a warning (not a block)
        when fake-data mode is off and credential fields are empty."""
        use_fake = self.fake_data_checkbox.isChecked()
        values = {
            "SyncroSubDomain": self.syncro_subdomain.text().strip(),
            "SyncroAPIKey": self.syncro_api_key.text().strip(),
            "HuntressAPIKey": self.huntress_api_key.text().strip(),
            "HuntressSecretKey": self.huntress_secret.text().strip(),
        }

        for key, value in values.items():
            self.settings_model.set(key, value)
        self.settings_model.set("UseFakeData", use_fake)
        self.settings_model.set("Debug", self.debug_checkbox.isChecked())

        if not self.settings_model.save():
            self.error_label.setText("Failed to save settings to disk.")
            self.error_label.setVisible(True)
            self.warning_label.setVisible(False)
            return

        self.error_label.setVisible(False)

        self._dirty = False

        missing = [key for key, value in values.items() if not value]
        if not use_fake and missing:
            self.warning_label.setText(
                "API keys are incomplete — real comparisons will fail until "
                "the missing fields are filled in: " + ", ".join(missing)
            )
            self.warning_label.setVisible(True)
            return

        self.warning_label.setVisible(False)
        self.saved.emit()
