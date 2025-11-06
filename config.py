import os
import json
from typing import Dict

def init_settings() -> Dict[str, str]:
    """Initialize and load settings from settings.json"""
    default_settings = {
        "SyncroAPIKey": "",
        "SyncroSubDomain": "",
        "HuntressAPIKey": "",
        "huntressApiSecretKey": "",
        "debug": False
    }

    if not os.path.exists("settings.json"):
        print("Settings file does not exist...\nCreating template file")
        with open("settings.json", "w") as f:
            f.write(json.dumps(default_settings, indent=4))

    with open("settings.json", "r") as f:
        settings = json.loads(f.read())
    
    # Validate settings
    loading_failed = False
    for key, value in settings.items():
        if value == "":
            print(f"{key} is missing a value in settings.json. Please fill out data")
            loading_failed = True
    
    if loading_failed:
        print("Settings file is missing data, exiting...")
        exit(1)
    
    return settings