"""Constants for the Syncro/Huntress Comparison Tool."""

# Asset name matching width.
#
# Syncro stores the Windows NetBIOS computer name, which Windows caps at 15
# characters, while Huntress stores the full hostname. Truncating both sides to
# 15 chars before comparing is therefore load-bearing: it lets a Syncro asset
# like "ORINLAW-TERRAHL" match the Huntress agent "OrinLaw-TerrahLaptop" (same
# machine). Do NOT remove this without re-validating matches against real data.
MAX_NAME_WIDTH = 15

# Comparison status values (single source of truth).
STATUS_OK = "OK!"
STATUS_MISSING_HUNTRESS = "Missing in Huntress"
STATUS_MISSING_SYNCRO = "Missing in Syncro"

# Canonical settings schema, shared by the CLI (config.py) and GUI
# (gui/models/settings_model.py) so the two cannot drift.
DEFAULT_SETTINGS = {
    "SyncroAPIKey": "",
    "SyncroSubDomain": "",
    "HuntressAPIKey": "",
    "HuntressSecretKey": "",
    "Debug": False,
    # Normalized (NetBIOS-truncated, lowercased) hostnames to treat as ignored.
    "IgnoredAssets": [],
    # Organization (Syncro customer) names to hide from results.
    "ExcludedOrganizations": [],
}

# Required credential fields that must be non-empty before a comparison runs.
REQUIRED_SETTINGS = [
    "SyncroAPIKey",
    "SyncroSubDomain",
    "HuntressAPIKey",
    "HuntressSecretKey",
]

# Syncro Constants
SYNCRO_BASE_URL_TEMPLATE = "https://{subdomain}.syncromsp.com/api/v1/"
SYNCRO_RATE_LIMIT = 3.0  # requests per second
SYNCRO_BURST = 180.0

# Huntress Constants
HUNTRESS_API_URL = "https://api.huntress.io/v1/agents"
HUNTRESS_ORGANIZATIONS_URL = "https://api.huntress.io/v1/organizations"
HUNTRESS_RATE_LIMIT = 60.0  # requests per second
