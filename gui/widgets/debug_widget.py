"""Debug view widget for raw API data."""

import json

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class DebugWidget(QWidget):
    """Widget for viewing raw API response data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_data = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)

        # Tab widget for different data views
        self.tabs = QTabWidget()

        # Syncro data tab
        self.syncro_text = QPlainTextEdit()
        self.syncro_text.setReadOnly(True)
        self.syncro_text.setPlaceholderText(
            "Run a comparison to see raw Syncro API data"
        )
        self.tabs.addTab(self.syncro_text, "Syncro Assets")

        # Huntress data tab
        self.huntress_text = QPlainTextEdit()
        self.huntress_text.setReadOnly(True)
        self.huntress_text.setPlaceholderText(
            "Run a comparison to see raw Huntress API data"
        )
        self.tabs.addTab(self.huntress_text, "Huntress Agents")

        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("Save Debug Data")
        self.save_btn.clicked.connect(self._save_data)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_data)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

    @Slot(dict)
    def set_raw_data(self, data: dict):
        """Set the raw API data."""
        self._raw_data = data

        # Format and display Syncro data
        syncro_data = data.get("syncro", [])
        self.syncro_text.setPlainText(json.dumps(syncro_data, indent=2, default=str))

        # Format and display Huntress data
        huntress_data = data.get("huntress", [])
        self.huntress_text.setPlainText(
            json.dumps(huntress_data, indent=2, default=str)
        )

        self.save_btn.setEnabled(True)

    @Slot()
    def clear_data(self):
        """Clear all debug data."""
        self._raw_data = {}
        self.syncro_text.clear()
        self.huntress_text.clear()
        self.save_btn.setEnabled(False)

    @Slot()
    def _save_data(self):
        """Save debug data to files."""
        if not self._raw_data:
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Debug Files")

        if not folder:
            return

        try:
            # Save Syncro data
            syncro_path = f"{folder}/debug_syncro.json"
            with open(syncro_path, "w") as f:
                json.dump(self._raw_data.get("syncro", []), f, indent=2, default=str)

            # Save Huntress data
            huntress_path = f"{folder}/debug_huntress.json"
            with open(huntress_path, "w") as f:
                json.dump(self._raw_data.get("huntress", []), f, indent=2, default=str)

            QMessageBox.information(
                self,
                "Success",
                f"Debug data saved to:\n{syncro_path}\n{huntress_path}",
            )
        except IOError as e:
            QMessageBox.critical(self, "Error", f"Failed to save debug data: {e}")
