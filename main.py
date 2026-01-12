import argparse
import json
import os
import sys

from rich.console import Console

from api.client import HuntressClient, SyncroClient
from config import ConfigurationError, load_settings
from services.comparison import ComparisonService
from utils.output import RichSpinner, print_colored_table, write_ascii_table, write_csv

console = Console()


def create_parser():
    parser = argparse.ArgumentParser(description="Compare Syncro and Huntress agents")

    parser.add_argument(
        "-c",
        "--compare",
        action="store_true",
        help="Compare Syncro and Huntress agents",
    )
    parser.add_argument("-o", "--output", metavar="FILE", help="Output results to file")
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "ascii"],
        default="csv",
        help="Output file format (default: csv)",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
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
            # Initialize Clients
            syncro_client = SyncroClient(
                api_key=settings["SyncroAPIKey"], subdomain=settings["SyncroSubDomain"]
            )
            huntress_client = HuntressClient(
                api_key=settings["HuntressAPIKey"],
                secret_key=settings["huntressApiSecretKey"],
            )

            # Initialize Service
            service = ComparisonService(syncro_client, huntress_client)

            # Fetch and Compare
            with RichSpinner("Fetching and comparing agents..."):
                result = (
                    service.fetch_and_compare()
                )  # This now happens in worker thread inside service if we wanted.
                # Actually fetch_and_compare uses ThreadPoolExecutor internally.

            # Debug Output
            if settings.get("debug"):
                os.makedirs("debug", exist_ok=True)
                with open("debug/agentDumpSyncro.json", "w") as f:
                    json.dump(result.syncro_assets, f, indent=4)
                with open("debug/agentDumpHuntress.json", "w") as f:
                    json.dump(result.huntress_agents, f, indent=4)

            # Output Results
            if args.output:
                try:
                    if args.format == "csv":
                        write_csv(args.output, result.rows)
                    elif args.format == "ascii":
                        write_ascii_table(
                            args.output,
                            result.rows,
                            result.syncro_count,
                            result.huntress_count,
                        )
                    console.print(f"[green]Results written to {args.output}[/green]")
                except Exception as e:
                    console.print(
                        f"[red]Failed to write {args.format.upper()} "
                        f"{args.output}: {e}[/red]"
                    )

            # Print to console
            print_colored_table(
                result.rows,
                not args.no_color,
                result.syncro_count,
                result.huntress_count,
            )

        except Exception as e:
            console.print(
                f"[bold red]An error occurred during comparison:[/bold red] {e}"
            )
            if settings.get("debug"):
                console.print_exception()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
