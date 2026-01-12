import json
from pathlib import Path
from typing import Dict, Any

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass

def load_settings(path: str = "settings.json") -> Dict[str, Any]:
    """
    Initialize and load settings from settings.json.
    
    Returns:
        Dict containing the settings.
        
    Raises:
        ConfigurationError: If settings are invalid or cannot be loaded.
    """
    settings_path = Path(path)
    
    default_settings = {
        "SyncroAPIKey": "",
        "SyncroSubDomain": "",
        "HuntressAPIKey": "",
        "huntressApiSecretKey": "",
        "debug": False
    }

    if not settings_path.exists():
        try:
            with open(settings_path, "w") as f:
                json.dump(default_settings, f, indent=4)
        except IOError as e:
            raise ConfigurationError(f"Failed to create settings template: {e}")
        
        # We created the template, but we still need valid settings to proceed
        # Depending on design, we might want to raise here to tell user to fill it out
        # But per original logic, it just creates it. We will raise below if empty.

    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ConfigurationError(f"Failed to load settings file: {e}")
    
    # Merge with defaults to ensure all keys exist
    # This handles case where user has old settings file missing new keys
    final_settings = default_settings.copy()
    final_settings.update(settings)
    
    # Validate required fields
    missing_fields = []
    for key, value in final_settings.items():
        if key in default_settings and isinstance(value, str) and not value and key != "debug":
            missing_fields.append(key)
    
    if missing_fields:
        raise ConfigurationError(
            f"Missing required settings: {', '.join(missing_fields)}. "
            f"Please populate {settings_path.absolute()}"
        )
    
    return final_settings

# Backwards compatibility if needed, or update consumers
def init_settings() -> Dict[str, str]:
    """Wrapper for load_settings to maintain simple API if needed, but better to use load_settings directly."""
    try:
        return load_settings()
    except ConfigurationError as e:
        print(f"Error: {e}")
        exit(1)