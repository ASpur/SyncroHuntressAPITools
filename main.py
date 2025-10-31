import os
import json
import base64
import sys
import requests
from requests.models import Response
from typing import Optional
import csv
try:
    import colorama
    colorama.init()
    COLORAMA_AVAILABLE = True
except Exception:
    COLORAMA_AVAILABLE = False



def initSettingsData():
    settings = {}
    settings["SyncroAPIKey"] = ""
    settings["SyncroSubDomain"] = ""
    settings["HuntressAPIKey"] = ""
    settings["huntressApiSecretKey"] = ""
    settings["debug"] = False

    if not os.path.exists("settings.json"):
        print( "Settings file does not exist...\nCreating template file")
        with open("settings.json", "w") as f:
            f.write(json.dumps(settings,indent=4))

    with open("settings.json","r") as f:
        jsonData = json.loads(f.read())

    for key, value in jsonData.items():
        settings[key] = jsonData[key]
    
    loadingFailed = False
    for key, value in settings.items():
        if(value == ""):
            print(key + " is missing a value in settings.json. Please fill out data")
            loadingFailed = True
    if(loadingFailed):
        print("settings file is missing data, exiting...")
        exit(1)
    return settings


def syncroRequest(settings, endpoint, paths = []) -> Response:
    request = "https://"+settings["SyncroSubDomain"]+".syncromsp.com/api/v1/"
    request += endpoint
    request += "?api_key=" + settings["SyncroAPIKey"]
    
    for path in paths:
        request += "&" + path

    response = requests.get(request, headers={"Accept": "application/json"})
    return response

def getSyncroTickets(settings, page = 1, openOnly = False):
    paths = ["page=" + str(page)]

    if openOnly:
        paths.append("status=Not%20Closed")

    responseContent = syncroRequest(settings, "tickets",paths).content
    tickets = json.loads(responseContent)["tickets"]
    return tickets

def getSyncroAssets(settings, page=1):
    paths = ["page=" + str(page)]

    responseContent = syncroRequest(settings, "customer_assets",paths).content
    assets = json.loads(responseContent)["assets"]
    return assets

def getAllSyncroAssets(settings, maxPages=50):
    assets = []
    for i in range(1,maxPages):
        newAssets = getSyncroAssets(settings, i)
        if(len(newAssets) <= 0):
            break
        assets += newAssets
    return assets
def getHuntressAgents(settings, page = 1, limit=500):
    authBytes = bytes(settings["HuntressAPIKey"]+":"+settings["huntressApiSecretKey"],'utf-8')
    auth = base64.b64encode(authBytes)
    auth = auth.decode('utf-8')

    request = f"https://api.huntress.io/v1/agents?page={page}&limit={limit}"
    headers = {"Authorization": "Basic " + auth}
    response = requests.get(request,headers=headers)
    return response.json()["agents"]

def compareAgents(settings, output_file: Optional[str] = None, use_color: bool = True, output_format: str = "console"):
    huntressAgents = getHuntressAgents(settings)
    syncroAssets = getAllSyncroAssets(settings)

    def normalize(name, length=15):
        if not name:
            return None
        return name.strip().lower()[:length]

    # Build maps from normalized -> set(original names)
    syncro_map = {}
    for a in syncroAssets:
        raw = a.get("name") or ""
        n = normalize(raw)
        if n:
            syncro_map.setdefault(n, set()).add(raw.strip())

    huntress_map = {}
    for a in huntressAgents:
        raw = a.get("hostname") or ""
        n = normalize(raw)
        if n:
            huntress_map.setdefault(n, set()).add(raw.strip())

    # Debug dumps (create folder if needed)
    if settings.get("debug"):
        os.makedirs("debug", exist_ok=True)
        with open("debug/agentDumpSyncro.json", "w") as f:
            f.write(json.dumps(syncroAssets, indent=4))
        with open("debug/agentDumpHuntress.json", "w") as f:
            f.write(json.dumps(huntressAgents, indent=4))

    # All keys and rows
    all_keys = sorted(set(syncro_map.keys()) | set(huntress_map.keys()))
    rows = []
    for key in all_keys:
        s_names = syncro_map.get(key)
        h_names = huntress_map.get(key)
        s_display = "; ".join(sorted(s_names)) if s_names else ""
        h_display = "; ".join(sorted(h_names)) if h_names else ""
        if s_names and h_names:
            status = "OK!"
        elif s_names and not h_names:
            status = "Missing in Huntress"
        else:
            status = "Missing in Syncro"
        rows.append((s_display, h_display, status))

    # sort so OK! rows come first, errors (missing) at the bottom; then alphabetical
    rows.sort(key=lambda r: (0 if r[2] == "OK!" else 1, r[0].lower(), r[1].lower()))

    # compute column widths
    col1w = max([len(r[0]) for r in rows] + [len("Syncro Asset")])
    col2w = max([len(r[1]) for r in rows] + [len("Huntress Asset")])
    col3w = max([len(r[2]) for r in rows] + [len("Status")])

    # Optionally write to file
    if output_file:
        try:
            if output_format == "csv":
                with open(output_file, "w", newline="", encoding="utf-8") as csvf:
                    writer = csv.writer(csvf)
                    writer.writerow(["Syncro Asset", "Huntress Asset", "Status"])
                    for r in rows:
                        writer.writerow(r)
            elif output_format == "ascii":
                with open(output_file, "w", encoding="utf-8") as f:
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
        except Exception as e:
            print(f"Failed to write {output_format.upper()} {output_file}: {e}")

    # Print table with color to console
    use_color = use_color and COLORAMA_AVAILABLE
    if use_color:
        GREEN = colorama.Fore.GREEN
        YELLOW = colorama.Fore.YELLOW
        RED = colorama.Fore.RED
        RESET = colorama.Style.RESET_ALL
    else:
        GREEN = YELLOW = RED = RESET = ""

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

def main():
    settings = initSettingsData()
    
    args = parse_arguments()
    
    if args.get('compare'):
        compareAgents(settings, 
                     output_file=args.get('output'), 
                     use_color=args.get('color', True),
                     output_format=args.get('format', 'console'))
    else:
        print("Usage: python main.py [command] [options]")
        print("Commands:")
        print("  -c, --compare           Compare Syncro and Huntress agents")
        print("Options:")
        print("  -o, --output FILE       Output results to file")
        print("  -f, --format FORMAT     Output format: csv or ascii (default: csv)")
        print("  --no-color             Disable colored output")

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
                    i += 1  # This line was missing!
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
    if 'color' not in args:
        args['color'] = True
    if 'format' not in args:
        args['format'] = 'csv'
    
    return args

if __name__ == "__main__":
    main()