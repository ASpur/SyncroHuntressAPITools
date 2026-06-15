"""Settings data model for managing application configuration."""

import copy
import json
import os
from typing import Dict, List, Set, Tuple

from PySide6.QtCore import QObject, Signal

from const import DEFAULT_SETTINGS, REQUIRED_SETTINGS


class SettingsModel(QObject):
    """Manages settings persistence and validation."""

    settings_changed = Signal()

    SETTINGS_FILE = "settings.json"
    REQUIRED_FIELDS = REQUIRED_SETTINGS
    DEFAULT_SETTINGS = DEFAULT_SETTINGS

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings: Dict = {}
        self.load()

    def load(self) -> Dict:
        """Load settings from file, create default if missing."""
        if not os.path.exists(self.SETTINGS_FILE):
            self._settings = copy.deepcopy(self.DEFAULT_SETTINGS)
            self.save()
        else:
            try:
                with open(self.SETTINGS_FILE, "r") as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._settings = copy.deepcopy(self.DEFAULT_SETTINGS)

        # Ensure all keys exist
        for key, default in self.DEFAULT_SETTINGS.items():
            if key not in self._settings:
                self._settings[key] = copy.deepcopy(default)

        return self._settings

    def save(self) -> bool:
        """Save current settings to file."""
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump(self._settings, f, indent=4)
            self.settings_changed.emit()
            return True
        except IOError:
            return False

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all required fields. Returns (is_valid, error_list)."""
        errors = []
        for field in self.REQUIRED_FIELDS:
            value = self._settings.get(field, "")
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field} is required")
        return (len(errors) == 0, errors)

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value."""
        self._settings[key] = value

    def get_all(self) -> Dict:
        """Get all settings as a dictionary."""
        return self._settings.copy()

    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return bool(self._settings.get("Debug", False))

    # --- Ignored assets (keyed by normalized comparison hostname) ---

    def get_ignored(self) -> Set[str]:
        """Return the set of ignored asset keys."""
        return set(self._settings.get("IgnoredAssets", []))

    def add_ignored(self, key: str) -> None:
        """Mark an asset key as ignored and persist."""
        ignored = self.get_ignored()
        if key not in ignored:
            ignored.add(key)
            self._settings["IgnoredAssets"] = sorted(ignored)
            self.save()

    def remove_ignored(self, key: str) -> None:
        """Un-ignore an asset key and persist."""
        ignored = self.get_ignored()
        if key in ignored:
            ignored.discard(key)
            self._settings["IgnoredAssets"] = sorted(ignored)
            self.save()

    # --- Excluded organizations ---

    def get_excluded_orgs(self) -> Set[str]:
        """Return the set of organization names to hide."""
        return set(self._settings.get("ExcludedOrganizations", []))

    def set_excluded_orgs(self, orgs: Set[str]) -> None:
        """Replace the excluded-organizations set and persist."""
        self._settings["ExcludedOrganizations"] = sorted(orgs)
        self.save()
