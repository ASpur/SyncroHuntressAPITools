import json
from pathlib import Path
from typing import Any, Dict


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
        "HuntressSecretKey": "",
        "Debug": False,
    }

    if not settings_path.exists():
        try:
            with open(settings_path, "w") as f:
                json.dump(default_settings, f, indent=4)
        except IOError as e:
            raise ConfigurationError(f"Failed to create settings template: {e}")

    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ConfigurationError(f"Failed to load settings file: {e}")

    # Migration: Check for old keys and migrate to new keys
    migrations_needed = False
    
    # huntressApiSecretKey -> HuntressSecretKey
    if "huntressApiSecretKey" in settings:
        if not settings.get("HuntressSecretKey"):  # Only if new key not already set
            settings["HuntressSecretKey"] = settings.pop("huntressApiSecretKey")
            migrations_needed = True
        else:
            # Both exist? Remove old one
            settings.pop("huntressApiSecretKey")
            migrations_needed = True

    # debug -> Debug
    if "debug" in settings:
        # Check type to avoid confusion if user has both
        if "Debug" not in settings:
            settings["Debug"] = settings.pop("debug")
            migrations_needed = True
        else:
            settings.pop("debug")
            migrations_needed = True

    if migrations_needed:
        try:
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
        except IOError:
            # Warn but don't fail, we can still proceed with memory values
            print(f"Warning: Failed to save migrated settings to {settings_path}")

    # Merge with defaults to ensure all keys exist
    final_settings = default_settings.copy()
    final_settings.update(settings)

    # Validate required fields
    missing_fields = []
    for key, value in final_settings.items():
        if (
            key in default_settings
            and isinstance(value, str)
            and not value
            and key != "Debug"
        ):
            missing_fields.append(key)

    if missing_fields:
        raise ConfigurationError(
            f"Missing required settings: {', '.join(missing_fields)}. "
            f"Please populate {settings_path.absolute()}"
        )

    return final_settings


# Backwards compatibility if needed, or update consumers
def init_settings() -> Dict[str, str]:
    """
    Wrapper for load_settings to maintain simple API if needed,
    but better to use load_settings directly.
    """
    try:
        return load_settings()
    except ConfigurationError as e:
        print(f"Error: {e}")
        exit(1)
