import csv
import sys
import threading
import time
from typing import List, Tuple

try:
    import colorama
    colorama.init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class Spinner:
    """A loading spinner for long-running operations."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Loading"):
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            sys.stdout.write(f"\r{frame} {self.message}...")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 5) + "\r")
        sys.stdout.flush()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

# Constants
HEADERS = ("Syncro Asset", "Huntress Asset", "Status")
STATUS_OK = "OK!"


def _calculate_column_widths(rows: List[Tuple[str, str, str]]) -> List[int]:
    """Calculate the width needed for each column based on content."""
    return [
        max(len(header), max((len(row[i]) for row in rows), default=0))
        for i, header in enumerate(HEADERS)
    ]


def _make_border(widths: List[int], fill_char: str = "-") -> str:
    """Generate a table border line like +----+----+----+"""
    return "+" + "+".join(fill_char * (w + 2) for w in widths) + "+"


def write_csv(filename: str, rows: List[Tuple[str, str, str]]) -> None:
    """Write results to CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def write_ascii_table(filename: str, rows: List[Tuple[str, str, str]]) -> None:
    """Write results to ASCII table file."""
    widths = _calculate_column_widths(rows)

    def format_row(values: Tuple[str, str, str]) -> str:
        cells = " | ".join(val.ljust(widths[i]) for i, val in enumerate(values))
        return f"| {cells} |"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(_make_border(widths) + "\n")
        f.write(format_row(HEADERS) + "\n")
        f.write(_make_border(widths, "=") + "\n")
        for row in rows:
            f.write(format_row(row) + "\n")
        f.write(_make_border(widths) + "\n")


def print_colored_table(rows: List[Tuple[str, str, str]], use_color: bool = True) -> None:
    """Print colored table to console."""
    use_color = use_color and COLORAMA_AVAILABLE

    if use_color:
        GREEN = colorama.Fore.GREEN
        RED = colorama.Fore.RED
        RESET = colorama.Style.RESET_ALL
    else:
        GREEN = RED = RESET = ""

    widths = _calculate_column_widths(rows)

    header = "  ".join(h.ljust(widths[i]) for i, h in enumerate(HEADERS))
    print(header)
    print("-" * (sum(widths) + 4))

    for syncro, huntress, status in rows:
        color = GREEN if status == STATUS_OK else RED
        print(f"{syncro.ljust(widths[0])}  {huntress.ljust(widths[1])}  {color}{status.ljust(widths[2])}{RESET}")
