import argparse
import sys
from config import load_settings, ConfigurationError
from services.comparison import compare_agents
from rich.console import Console

console = Console()

def create_parser():
    parser = argparse.ArgumentParser(
        description="Compare Syncro and Huntress agents"
    )

    parser.add_argument(
        "-c", "--compare",
        action="store_true",
        help="Compare Syncro and Huntress agents"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Output results to file"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["csv", "ascii"],
        default="csv",
        help="Output file format (default: csv)"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)

    if args.compare:
        try:
            compare_agents(
                settings,
                output_file=args.output,
                use_color=not args.no_color,
                output_format=args.format
            )
        except Exception as e:
            console.print(f"[bold red]An error occurred during comparison:[/bold red] {e}")
            if settings.get("debug"):
                console.print_exception()
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()