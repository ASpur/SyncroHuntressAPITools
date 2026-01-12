"""Settings configuration widget."""

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.models.settings_model import SettingsModel


class SettingsWidget(QWidget):
    """Widget for editing API settings."""

    def __init__(self, settings_model: SettingsModel, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)

        # Syncro settings group
        syncro_group = QGroupBox("Syncro MSP Settings")
        syncro_layout = QFormLayout(syncro_group)

        self.syncro_subdomain = QLineEdit()
        self.syncro_subdomain.setPlaceholderText("your-company")
        syncro_layout.addRow("Subdomain:", self.syncro_subdomain)

        self.syncro_api_key = QLineEdit()
        self.syncro_api_key.setEchoMode(QLineEdit.Password)
        self.syncro_api_key.setPlaceholderText("Enter Syncro API key")

        syncro_key_layout = QHBoxLayout()
        syncro_key_layout.addWidget(self.syncro_api_key)
        self.syncro_show_btn = QPushButton("Show")
        self.syncro_show_btn.setCheckable(True)
        self.syncro_show_btn.toggled.connect(
            lambda checked: self.syncro_api_key.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        self.syncro_show_btn.toggled.connect(
            lambda checked: self.syncro_show_btn.setText("Hide" if checked else "Show")
        )
        syncro_key_layout.addWidget(self.syncro_show_btn)
        syncro_layout.addRow("API Key:", syncro_key_layout)

        layout.addWidget(syncro_group)

        # Huntress settings group
        huntress_group = QGroupBox("Huntress Settings")
        huntress_layout = QFormLayout(huntress_group)

        self.huntress_api_key = QLineEdit()
        self.huntress_api_key.setEchoMode(QLineEdit.Password)
        self.huntress_api_key.setPlaceholderText("Enter Huntress API key")

        huntress_key_layout = QHBoxLayout()
        huntress_key_layout.addWidget(self.huntress_api_key)
        self.huntress_show_btn = QPushButton("Show")
        self.huntress_show_btn.setCheckable(True)
        self.huntress_show_btn.toggled.connect(
            lambda checked: self.huntress_api_key.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        self.huntress_show_btn.toggled.connect(
            lambda checked: self.huntress_show_btn.setText(
                "Hide" if checked else "Show"
            )
        )
        huntress_key_layout.addWidget(self.huntress_show_btn)
        huntress_layout.addRow("API Key:", huntress_key_layout)

        self.huntress_secret = QLineEdit()
        self.huntress_secret.setEchoMode(QLineEdit.Password)
        self.huntress_secret.setPlaceholderText("Enter Huntress secret key")

        huntress_secret_layout = QHBoxLayout()
        huntress_secret_layout.addWidget(self.huntress_secret)
        self.huntress_secret_show_btn = QPushButton("Show")
        self.huntress_secret_show_btn.setCheckable(True)
        self.huntress_secret_show_btn.toggled.connect(
            lambda checked: self.huntress_secret.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        self.huntress_secret_show_btn.toggled.connect(
            lambda checked: self.huntress_secret_show_btn.setText(
                "Hide" if checked else "Show"
            )
        )
        huntress_secret_layout.addWidget(self.huntress_secret_show_btn)
        huntress_layout.addRow("Secret Key:", huntress_secret_layout)

        layout.addWidget(huntress_group)

        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.debug_checkbox = QCheckBox("Enable debug mode (saves raw API responses)")
        options_layout.addWidget(self.debug_checkbox)

        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._load_values)
        button_layout.addWidget(self.reset_btn)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Add stretch to push everything to top
        layout.addStretch()

    def _load_values(self):
        """Load values from settings model into UI."""
        self.syncro_subdomain.setText(self.settings_model.get("SyncroSubDomain", ""))
        self.syncro_api_key.setText(self.settings_model.get("SyncroAPIKey", ""))
        self.huntress_api_key.setText(self.settings_model.get("HuntressAPIKey", ""))
        self.huntress_secret.setText(
            self.settings_model.get("huntressApiSecretKey", "")
        )
        self.debug_checkbox.setChecked(self.settings_model.get("debug", False))
        self.status_label.setText("")

    @Slot()
    def _save_settings(self):
        """Save current UI values to settings model."""
        self.settings_model.set("SyncroSubDomain", self.syncro_subdomain.text().strip())
        self.settings_model.set("SyncroAPIKey", self.syncro_api_key.text().strip())
        self.settings_model.set("HuntressAPIKey", self.huntress_api_key.text().strip())
        self.settings_model.set(
            "huntressApiSecretKey", self.huntress_secret.text().strip()
        )
        self.settings_model.set("debug", self.debug_checkbox.isChecked())

        if self.settings_model.save():
            self.status_label.setText("Settings saved successfully!")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Failed to save settings")
            self.status_label.setStyleSheet("color: red;")
