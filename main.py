import os
import json
import base64
import requests
from requests.models import Response



def initSettingsData():
    settings = {}
    settings["SyncroAPIKey"] = ""
    settings["SyncroSubDomain"] = ""
    settings["HuntressAPIKey"] = ""
    settings["huntressApiSecretKey"] = ""

    if not os.path.exists("settings.json"):
        print( "Settings file does not exist...\nCreating template file")
        with open("settings.json", "w") as file:
            file.write(json.dumps(settings,indent=4))

    with open("settings.json","r") as file:
        jsonData = json.loads(file.read())

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
settings = initSettingsData()


def syncroRequest(endpoint, paths = []) -> Response:
    request = "https://"+settings["SyncroSubDomain"]+".syncromsp.com/api/v1/"
    request += endpoint
    request += "?api_key=" + settings["SyncroAPIKey"]
    
    for path in paths:
        request += "&" + path

    response = requests.get(request, headers={"Accept": "application/json"})
    return response

def getSyncroTickets(page = 1, openOnly = False):
    paths = ["page=" + str(page)]

    if openOnly:
        paths.append("status=Not%20Closed")

    responseContent = syncroRequest("tickets",paths).content
    tickets = json.loads(responseContent)["tickets"]
    return tickets

def getSyncroAssets(page=1):
    paths = ["page=" + str(page)]

    responseContent = syncroRequest("customer_assets",paths).content
    assets = json.loads(responseContent)["assets"]
    return assets

def getAllSyncroAssets(maxPages=50):
    assets = []
    for i in range(1,maxPages):
        newAssets = getSyncroAssets(i)
        if(len(newAssets) <= 0):
            break
        assets += newAssets
    return assets

def getHuntressAgents(page = 1, limit=500):
    authBytes = bytes(settings["HuntressAPIKey"]+":"+settings["huntressApiSecretKey"],'utf-8')
    auth = base64.b64encode(authBytes)
    auth = auth.decode('utf-8')

    request = f"https://api.huntress.io/v1/agents?page={page}&limit={limit}"
    headers = {"Authorization": "Basic " + auth}
    response = requests.get(request,headers=headers)
    return response.json()["agents"]

def compareAgents():
    huntressAgents = getHuntressAgents()
    syncroAssets = getAllSyncroAssets()

    for sa in syncroAssets:
        saName = sa["properties"]["device_name"].lower()
        found = False
        for ha in huntressAgents:
            #only checking first 15 characters because syncro cuts the name off at 15
            if(ha["hostname"].lower()[:15] == saName):
                found = True
                break
        if(not found):
            print(saName + " has no match in Huntress")
    for ha in huntressAgents:
        haName = ha["hostname"][:15]
        found = False
        for sa in syncroAssets:
            if(sa["properties"]["device_name"].lower() == haName.lower()):
                found = True
                break
        if(not found):
            print(haName + " has no match in Syncro")

compareAgents()
