"""Modal dialog for inspecting and saving raw API response data."""

import json

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)


class DebugDialog(QDialog):
    """Show the raw Syncro/Huntress payloads from the last comparison run."""

    def __init__(self, raw_data: dict, parent=None):
        super().__init__(parent)
        self._raw_data = raw_data or {}
        self.setWindowTitle("Debug data")
        self.setMinimumSize(640, 480)
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.syncro_text = QPlainTextEdit()
        self.syncro_text.setReadOnly(True)
        self.syncro_text.setPlaceholderText("Run a comparison to see raw Syncro data")
        self.tabs.addTab(self.syncro_text, "Syncro assets")
        self.huntress_text = QPlainTextEdit()
        self.huntress_text.setReadOnly(True)
        self.huntress_text.setPlaceholderText(
            "Run a comparison to see raw Huntress data"
        )
        self.tabs.addTab(self.huntress_text, "Huntress agents")
        layout.addWidget(self.tabs)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save to folder…")
        self.save_btn.clicked.connect(self._save_data)
        buttons.addWidget(self.save_btn)
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setProperty("variant", "primary")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _populate(self):
        syncro = self._raw_data.get("syncro", [])
        huntress = self._raw_data.get("huntress", [])
        self.syncro_text.setPlainText(json.dumps(syncro, indent=2, default=str))
        self.huntress_text.setPlainText(json.dumps(huntress, indent=2, default=str))
        self.save_btn.setEnabled(bool(self._raw_data))

    @Slot()
    def _save_data(self):
        if not self._raw_data:
            return
        folder = QFileDialog.getExistingDirectory(self, "Select folder for debug files")
        if not folder:
            return
        try:
            syncro_path = f"{folder}/debug_syncro.json"
            with open(syncro_path, "w") as f:
                json.dump(self._raw_data.get("syncro", []), f, indent=2, default=str)
            huntress_path = f"{folder}/debug_huntress.json"
            with open(huntress_path, "w") as f:
                json.dump(self._raw_data.get("huntress", []), f, indent=2, default=str)
            QMessageBox.information(
                self, "Saved", f"Debug data saved to:\n{syncro_path}\n{huntress_path}"
            )
        except IOError as e:
            QMessageBox.critical(self, "Error", f"Failed to save debug data: {e}")
