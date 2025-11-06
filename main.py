import sys
from config import init_settings
from services.comparison import compare_agents

def parse_arguments():
    """Parse command line arguments and return a dictionary of options"""
    args = {}
    i = 1
    
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ['-c', '--compare']:
            args['compare'] = True
        elif arg in ['-o', '--output']:
            if i + 1 < len(sys.argv):
                args['output'] = sys.argv[i + 1]
                i += 1
            else:
                print("Error: -o/--output requires a filename")
                sys.exit(1)
        elif arg in ['-f', '--format']:
            if i + 1 < len(sys.argv):
                fmt = sys.argv[i + 1].lower()
                if fmt in ['csv', 'ascii']:
                    args['format'] = fmt
                    i += 1
                else:
                    print("Error: format must be 'csv' or 'ascii'")
                    sys.exit(1)
            else:
                print("Error: -f/--format requires a format type (csv or ascii)")
                sys.exit(1)
        elif arg == '--no-color':
            args['color'] = False
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
        
        i += 1
    
    # Set defaults
    args.setdefault('color', True)
    args.setdefault('format', 'csv')
    
    return args

def main():
    settings = init_settings()
    args = parse_arguments()
    
    if args.get('compare'):
        compare_agents(
            settings,
            output_file=args.get('output'),
            use_color=args.get('color', True),
            output_format=args.get('format', 'csv')
        )
    else:
        print("Usage: python main.py [command] [options]")
        print("Commands:")
        print("  -c, --compare           Compare Syncro and Huntress agents")
        print("Options:")
        print("  -o, --output FILE       Output results to file")
        print("  -f, --format FORMAT     Output format: csv or ascii (default: csv)")
        print("  --no-color              Disable colored output")

if __name__ == "__main__":
    main()