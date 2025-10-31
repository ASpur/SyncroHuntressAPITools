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

def compareAgents(settings, output_file: Optional[str] = None, use_color: bool = True):
    huntressAgents = getHuntressAgents(settings)
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

    # Optionally write CSV
    if output_file:
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvf:
                writer = csv.writer(csvf)
                writer.writerow(["Syncro Asset", "Huntress Asset", "Status"])
                for r in rows:
                    writer.writerow(r)
        except Exception as e:
            print(f"Failed to write CSV {output_file}: {e}")

    # Print table with color
    use_color = use_color and COLORAMA_AVAILABLE
    if use_color:
        GREEN = colorama.Fore.GREEN
        YELLOW = colorama.Fore.YELLOW
        RED = colorama.Fore.RED
        RESET = colorama.Style.RESET_ALL
    else:
        GREEN = YELLOW = RED = RESET = ""

    # compute column widths
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

def main():
    settings = initSettingsData()
    output_file = None
    use_color = True
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    if "--no-color" in sys.argv:
        use_color = False
    # run compare with optional output file and color flag
    compareAgents(settings, output_file=output_file, use_color=use_color)

if __name__ == "__main__":
    main()