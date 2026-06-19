"""Modal dialog for inspecting and saving raw API response data."""

import json
import re

from PySide6.QtCore import Slot
from PySide6.QtGui import QColor, QFont, QFontDatabase, QSyntaxHighlighter, QTextCharFormat
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


class JsonHighlighter(QSyntaxHighlighter):
    """Minimal syntax highlighter for JSON text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#1d9e75"))
        self._rules.append((re.compile(r'"[^"]*"\s*:'), string_fmt))
        self._rules.append((re.compile(r':\s*"[^"]*"'), string_fmt))

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#2f6db3"))
        self._rules.append((re.compile(r'\b-?\d+\.?\d*\b'), number_fmt))

        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#e0901a"))
        self._rules.append((re.compile(r'\b(true|false|null)\b'), keyword_fmt))

        brace_fmt = QTextCharFormat()
        brace_fmt.setForeground(QColor("#8a8a82"))
        self._rules.append((re.compile(r'[{}\[\]]'), brace_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


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

        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(10)

        self.tabs = QTabWidget()
        self.syncro_text = QPlainTextEdit()
        self.syncro_text.setReadOnly(True)
        self.syncro_text.setPlaceholderText("Run a comparison to see raw Syncro data")
        self.syncro_text.setFont(mono)
        self._syncro_highlighter = JsonHighlighter(self.syncro_text.document())
        self.tabs.addTab(self.syncro_text, "Syncro assets")
        self.huntress_text = QPlainTextEdit()
        self.huntress_text.setReadOnly(True)
        self.huntress_text.setPlaceholderText(
            "Run a comparison to see raw Huntress data"
        )
        self.huntress_text.setFont(mono)
        self._huntress_highlighter = JsonHighlighter(self.huntress_text.document())
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
