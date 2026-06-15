import csv
from unittest.mock import patch

from services.comparison import ComparisonRow
from utils.output import HEADERS, print_colored_table, write_ascii_table, write_csv


def _row(org, syncro, huntress, status):
    return ComparisonRow(
        syncro_name=syncro,
        huntress_name=huntress,
        status=status,
        organization=org,
    )


class TestWriteCSV:
    def test_writes_correct_content(self, tmp_path):
        """Test that CSV is written with org column, headers and data."""
        filepath = tmp_path / "test.csv"
        rows = [
            _row("Acme", "Asset1", "Agent1", "OK!"),
            _row("", "Asset2", "", "Missing in Huntress"),
        ]

        write_csv(str(filepath), rows)

        assert filepath.exists()
        with open(filepath, "r", encoding="utf-8") as f:
            lines = list(csv.reader(f))

        assert lines[0] == list(HEADERS) + ["Ignored"]
        assert lines[1] == ["Acme", "Asset1", "Agent1", "OK!", ""]
        assert lines[2] == ["", "Asset2", "", "Missing in Huntress", ""]

    def test_marks_ignored_rows(self, tmp_path):
        """Ignored assets are flagged in the Ignored column."""
        filepath = tmp_path / "ig.csv"
        rows = [_row("Acme", "PC-1", "", "Missing in Huntress")]

        write_csv(str(filepath), rows, ignored_keys={"pc-1"})

        with open(filepath, "r", encoding="utf-8") as f:
            lines = list(csv.reader(f))
        assert lines[1][-1] == "yes"

    def test_handles_io_error(self, capsys):
        """Test that IOError is caught and printed."""
        write_csv("/", [])

        captured = capsys.readouterr()
        assert (
            "Failed to write CSV" in captured.out
            or "Failed to write CSV" in captured.err
        )


class TestWriteAsciiTable:
    def test_writes_formatted_table(self, tmp_path):
        """Test that ASCII table is written with alignment."""
        filepath = tmp_path / "table.txt"
        rows = [_row("Acme", "Short", "LongerName", "OK!")]

        write_ascii_table(str(filepath), rows, syncro_count=1, huntress_count=1)

        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")

        assert "Asset Counts" in content
        assert "Syncro:   1" in content
        assert "Huntress: 1" in content

        assert "Organization" in content
        assert "Syncro Asset" in content
        assert "Huntress Asset" in content

        assert "Acme" in content
        assert "Short" in content
        assert "LongerName" in content
        assert "OK!" in content

    def test_empty_rows_still_writes_headers(self, tmp_path):
        filepath = tmp_path / "empty.txt"
        write_ascii_table(str(filepath), [], syncro_count=0, huntress_count=0)
        content = filepath.read_text(encoding="utf-8")
        assert "Organization" in content

    def test_handles_io_error(self, capsys):
        """Test that IOError is handled."""
        write_ascii_table("/", [])

        captured = capsys.readouterr()
        assert "Failed to write ASCII table" in captured.out


class TestPrintColoredTable:
    @patch("utils.output.console")
    def test_prints_table_elements(self, mock_console):
        """Test that table is constructed and printed."""
        rows = [_row("Acme", "A", "B", "OK!")]
        print_colored_table(rows, syncro_count=5, huntress_count=5)

        assert mock_console.print.call_count >= 1

        calls = [str(c) for c in mock_console.print.mock_calls]
        assert any("Asset Counts" in c for c in calls)
        assert any("5" in c for c in calls)

    @patch("utils.output.console")
    def test_no_color_mode(self, mock_console):
        """Test that no_color mode doesn't crash."""
        print_colored_table([_row("Acme", "A", "B", "OK!")], use_color=False)

        assert mock_console.print.called
