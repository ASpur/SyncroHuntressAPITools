import csv
import os
from unittest.mock import Mock, patch

import pytest

from utils.output import HEADERS, print_colored_table, write_ascii_table, write_csv


class TestWriteCSV:
    def test_writes_correct_content(self, tmp_path):
        """Test that CSV is written with correct headers and data."""
        filepath = tmp_path / "test.csv"
        rows = [("Asset1", "Agent1", "OK!"), ("Asset2", "", "Missing")]

        write_csv(str(filepath), rows)

        assert filepath.exists()
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            lines = list(reader)

        assert lines[0] == list(HEADERS)
        assert lines[1] == ["Asset1", "Agent1", "OK!"]
        assert lines[2] == ["Asset2", "", "Missing"]

    def test_handles_io_error(self, capsys):
        """Test that IOError is caught and printed."""
        # Trying to write to a directory should raise IOError/IsADirectoryError
        write_csv("/", [])
        
        captured = capsys.readouterr()
        assert "Failed to write CSV" in captured.out or "Failed to write CSV" in captured.err
        # Note: rich console prints to stdout/stderr depending on config, usually stdout


class TestWriteAsciiTable:
    def test_writes_formatted_table(self, tmp_path):
        """Test that ASCII table is written with alignment."""
        filepath = tmp_path / "table.txt"
        rows = [("Short", "LongerName", "OK!")]

        write_ascii_table(str(filepath), rows, syncro_count=1, huntress_count=1)

        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")

        assert "Asset Counts" in content
        assert "Syncro:   1" in content
        assert "Huntress: 1" in content
        
        # Check for headers
        assert "Syncro Asset" in content
        assert "Huntress Asset" in content
        
        # Check for row content
        assert "Short" in content
        assert "LongerName" in content
        assert "OK!" in content

    def test_handles_io_error(self, capsys):
        """Test that IOError is handled."""
        write_ascii_table("/", [])
        
        captured = capsys.readouterr()
        assert "Failed to write ASCII table" in captured.out



class TestPrintColoredTable:
    @patch("utils.output.console")
    def test_prints_table_elements(self, mock_console):
        """Test that table is constructed and printed."""
        rows = [("A", "B", "OK!")]
        print_colored_table(rows, syncro_count=5, huntress_count=5)

        # Should verify Table was created and added to
        # Since Table is local to the function, we verify what was printed
        assert mock_console.print.call_count >= 1
        
        # Verify calls regarding counts
        calls = [str(c) for c in mock_console.print.mock_calls]
        assert any("Asset Counts" in c for c in calls)
        assert any("5" in c for c in calls)

    @patch("utils.output.console")
    def test_no_color_mode(self, mock_console):
        """Test that no_color mode doesn't crash."""
        print_colored_table([("A", "B", "OK!")], use_color=False)
        
        # Mainly checking implementation doesn't raise error
        assert mock_console.print.called
