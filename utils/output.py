import csv
from typing import List, Optional, Set

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from const import STATUS_OK
from services.comparison import ComparisonRow, row_key

# Constants
HEADERS = ("Organization", "Syncro Asset", "Huntress Asset", "Status")

console = Console()


class RichSpinner:
    """Wrapper around rich progress for spinner functionality."""

    def __init__(self, message: str = "Loading"):
        self.message = message
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        self.task = None

    def __enter__(self):
        self.progress.start()
        self.task = self.progress.add_task(description=self.message, total=None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()


def _values(row: ComparisonRow) -> tuple:
    """Project a ComparisonRow to ordered display values."""
    return (row.organization, row.syncro_name, row.huntress_name, row.status)


def _is_ignored(row: ComparisonRow, ignored_keys: Optional[Set[str]]) -> bool:
    return bool(ignored_keys) and row_key(row) in ignored_keys


def write_csv(
    filename: str,
    rows: List[ComparisonRow],
    ignored_keys: Optional[Set[str]] = None,
) -> None:
    """Write results to CSV file (with an Ignored column)."""
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvf:
            writer = csv.writer(csvf)
            writer.writerow(HEADERS + ("Ignored",))
            for row in rows:
                flag = "yes" if _is_ignored(row, ignored_keys) else ""
                writer.writerow(_values(row) + (flag,))
    except IOError as e:
        console.print(f"[red]Failed to write CSV: {e}[/red]")


def write_ascii_table(
    filename: str,
    rows: List[ComparisonRow],
    syncro_count: int = 0,
    huntress_count: int = 0,
    ignored_keys: Optional[Set[str]] = None,
) -> None:
    """Write results to ASCII table file."""
    try:
        headers = HEADERS + ("Ignored",)
        table_rows = [
            _values(row) + ("yes" if _is_ignored(row, ignored_keys) else "",)
            for row in rows
        ]

        with open(filename, "w", encoding="utf-8") as f:
            f.write("Asset Counts\n")
            f.write(f"  Syncro:   {syncro_count}\n")
            f.write(f"  Huntress: {huntress_count}\n\n")

            # Simple column width calc
            widths = (
                [max(len(str(val)) for val in col) for col in zip(headers, *table_rows)]
                if table_rows
                else [len(h) for h in headers]
            )
            widths = [max(w, len(h)) for h, w in zip(headers, widths)]

            header = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
            separator = "-+-".join("-" * w for w in widths)

            f.write(f"{header}\n{separator}\n")
            for row in table_rows:
                line = " | ".join(str(val).ljust(w) for val, w in zip(row, widths))
                f.write(f"{line}\n")

    except IOError as e:
        console.print(f"[red]Failed to write ASCII table: {e}[/red]")


def print_colored_table(
    rows: List[ComparisonRow],
    use_color: bool = True,
    syncro_count: int = 0,
    huntress_count: int = 0,
    ignored_keys: Optional[Set[str]] = None,
) -> None:
    """Print styled table to console using rich."""
    if not use_color:
        # Fallback for no-color request
        table = Table(show_header=True, header_style="bold")
    else:
        table = Table(show_header=True, header_style="bold magenta")

    for header in HEADERS:
        table.add_column(header)

    for row in rows:
        ignored = _is_ignored(row, ignored_keys)
        status_style = "green" if row.status == STATUS_OK else "red"
        if not use_color:
            status_style = None

        status_cell = (
            f"[{status_style}]{row.status}[/{status_style}]"
            if status_style
            else row.status
        )
        row_style = "dim" if ignored else None
        table.add_row(
            row.organization,
            row.syncro_name,
            row.huntress_name,
            status_cell,
            style=row_style,
        )

    console.print(table)
    console.print("\n[bold]Asset Counts[/bold]")
    console.print(f"  Syncro:   {syncro_count}")
    console.print(f"  Huntress: {huntress_count}")
