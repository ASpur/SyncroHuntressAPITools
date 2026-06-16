"""Modal settings dialog for API credentials and options."""

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.models.settings_model import SettingsModel


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


class SettingsDialog(QDialog):
    """Edit and persist API settings. Blocks until saved or cancelled."""

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self.setWindowTitle("Settings")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Syncro
        syncro_group = QGroupBox("Syncro MSP")
        syncro_form = QFormLayout(syncro_group)
        self.syncro_subdomain = QLineEdit()
        self.syncro_subdomain.setPlaceholderText("your-company")
        syncro_form.addRow("Subdomain:", self.syncro_subdomain)
        self.syncro_api_key = QLineEdit()
        self.syncro_api_key.setPlaceholderText("Enter Syncro API key")
        syncro_form.addRow("API key:", _key_row(self.syncro_api_key))
        layout.addWidget(syncro_group)

        # Huntress
        huntress_group = QGroupBox("Huntress")
        huntress_form = QFormLayout(huntress_group)
        self.huntress_api_key = QLineEdit()
        self.huntress_api_key.setPlaceholderText("Enter Huntress API key")
        huntress_form.addRow("API key:", _key_row(self.huntress_api_key))
        self.huntress_secret = QLineEdit()
        self.huntress_secret.setPlaceholderText("Enter Huntress secret key")
        huntress_form.addRow("Secret key:", _key_row(self.huntress_secret))
        layout.addWidget(huntress_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.debug_checkbox = QCheckBox("Enable debug mode (saves raw API responses)")
        options_layout.addWidget(self.debug_checkbox)
        layout.addWidget(options_group)

        # Inline validation message
        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Save / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_btn = buttons.button(QDialogButtonBox.Save)
        self.save_btn.setProperty("variant", "primary")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self):
        self.syncro_subdomain.setText(self.settings_model.get("SyncroSubDomain", ""))
        self.syncro_api_key.setText(self.settings_model.get("SyncroAPIKey", ""))
        self.huntress_api_key.setText(self.settings_model.get("HuntressAPIKey", ""))
        self.huntress_secret.setText(self.settings_model.get("HuntressSecretKey", ""))
        self.debug_checkbox.setChecked(self.settings_model.get("Debug", False))

    @Slot()
    def _on_save(self):
        """Validate the form; persist and accept only when all required fields set."""
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

        self.accept()
