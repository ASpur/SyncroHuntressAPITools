import argparse
from config import init_settings
from services.comparison import compare_agents


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
        help="Output format (default: csv)"
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
    settings = init_settings()

    if args.compare:
        compare_agents(
            settings,
            output_file=args.output,
            use_color=not args.no_color,
            output_format=args.format
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()