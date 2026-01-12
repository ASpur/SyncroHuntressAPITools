import csv
import sys
from typing import List, Tuple
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Constants
HEADERS = ("Syncro Asset", "Huntress Asset", "Status")
STATUS_OK = "OK!"

console = Console()

class RichSpinner:
    """Wrapper around rich progress for spinner functionality."""
    def __init__(self, message: str = "Loading"):
        self.message = message
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )
        self.task = None

    def __enter__(self):
        self.progress.start()
        self.task = self.progress.add_task(description=self.message, total=None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()

def write_csv(filename: str, rows: List[Tuple[str, str, str]]) -> None:
    """Write results to CSV file."""
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvf:
            writer = csv.writer(csvf)
            writer.writerow(HEADERS)
            writer.writerows(rows)
    except IOError as e:
        console.print(f"[red]Failed to write CSV: {e}[/red]")

def write_ascii_table(
    filename: str,
    rows: List[Tuple[str, str, str]],
    syncro_count: int = 0,
    huntress_count: int = 0
) -> None:
    """Write results to ASCII table file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # We can use rich's export functionality or keep simple ascii
            # For file output, simple string manipulation is often safer/cleaner than ensuring no ansi codes leak
            # Re-implementing simple ascii here for file safety, or could use console.print(file=f)
            
            f.write("Asset Counts\n")
            f.write(f"  Syncro:   {syncro_count}\n")
            f.write(f"  Huntress: {huntress_count}\n\n")
            
            # Simple column width calc
            widths = [max(len(str(val)) for val in col) for col in zip(HEADERS, *rows)]
            widths = [max(w, len(h)) for h, w in zip(HEADERS, widths)]
            
            header = " | ".join(h.ljust(w) for h, w in zip(HEADERS, widths))
            separator = "-+-".join("-" * w for w in widths)
            
            f.write(f"{header}\n{separator}\n")
            for row in rows:
                line = " | ".join(val.ljust(w) for val, w in zip(row, widths))
                f.write(f"{line}\n")
                
    except IOError as e:
        console.print(f"[red]Failed to write ASCII table: {e}[/red]")

def print_colored_table(
    rows: List[Tuple[str, str, str]],
    use_color: bool = True,
    syncro_count: int = 0,
    huntress_count: int = 0
) -> None:
    """Print styled table to console using rich."""
    if not use_color:
        # Fallback for no-color request
        table = Table(show_header=True, header_style="bold")
    else:
        table = Table(show_header=True, header_style="bold magenta")

    for header in HEADERS:
        table.add_column(header)

    for syncro, huntress, status in rows:
        status_style = "green" if status == STATUS_OK else "red"
        if not use_color:
            status_style = None
            
        table.add_row(syncro, huntress, f"[{status_style}]{status}[/{status_style}]" if status_style else status)

    console.print(table)
    console.print("\n[bold]Asset Counts[/bold]")
    console.print(f"  Syncro:   {syncro_count}")
    console.print(f"  Huntress: {huntress_count}")
