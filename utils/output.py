import csv
from typing import List, Tuple

try:
    import colorama
    colorama.init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

def write_csv(filename: str, rows: List[Tuple[str, str, str]]) -> None:
    """Write results to CSV file"""
    with open(filename, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["Syncro Asset", "Huntress Asset", "Status"])
        writer.writerows(rows)

def write_ascii_table(filename: str, rows: List[Tuple[str, str, str]]) -> None:
    """Write results to ASCII table file"""
    col1w = max([len(r[0]) for r in rows] + [len("Syncro Asset")])
    col2w = max([len(r[1]) for r in rows] + [len("Huntress Asset")])
    col3w = max([len(r[2]) for r in rows] + [len("Status")])

    with open(filename, "w", encoding="utf-8") as f:
        # Top border
        f.write("+" + "-" * (col1w + 2) + "+" + "-" * (col2w + 2) + "+" + "-" * (col3w + 2) + "+\n")
        # Header
        f.write(f"| {'Syncro Asset'.ljust(col1w)} | {'Huntress Asset'.ljust(col2w)} | {'Status'.ljust(col3w)} |\n")
        # Header separator
        f.write("+" + "=" * (col1w + 2) + "+" + "=" * (col2w + 2) + "+" + "=" * (col3w + 2) + "+\n")
        # Data rows
        for s, h, status in rows:
            f.write(f"| {s.ljust(col1w)} | {h.ljust(col2w)} | {status.ljust(col3w)} |\n")
        # Bottom border
        f.write("+" + "-" * (col1w + 2) + "+" + "-" * (col2w + 2) + "+" + "-" * (col3w + 2) + "+\n")

def print_colored_table(rows: List[Tuple[str, str, str]], use_color: bool = True) -> None:
    """Print colored table to console"""
    use_color = use_color and COLORAMA_AVAILABLE
    
    if use_color:
        GREEN = colorama.Fore.GREEN
        YELLOW = colorama.Fore.YELLOW
        RED = colorama.Fore.RED
        RESET = colorama.Style.RESET_ALL
    else:
        GREEN = YELLOW = RED = RESET = ""

    col1w = max([len(r[0]) for r in rows] + [len("Syncro Asset")])
    col2w = max([len(r[1]) for r in rows] + [len("Huntress Asset")])
    col3w = max([len(r[2]) for r in rows] + [len("Status")])

    header = f"{'Syncro Asset'.ljust(col1w)}  {'Huntress Asset'.ljust(col2w)}  {'Status'.ljust(col3w)}"
    print(header)
    print("-" * (col1w + col2w + col3w + 4))
    
    for s, h, status in rows:
        if status == "OK!":
            color = GREEN
        elif status == "Missing in Huntress":
            color = YELLOW
        else:
            color = RED
        print(f"{s.ljust(col1w)}  {h.ljust(col2w)}  {color}{status.ljust(col3w)}{RESET}")