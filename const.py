"""Constants for the Syncro/Huntress Comparison Tool."""

MAX_NAME_WIDTH = 15

# Syncro Constants
SYNCRO_BASE_URL_TEMPLATE = "https://{subdomain}.syncromsp.com/api/v1/"
SYNCRO_RATE_LIMIT = 3.0  # requests per second
SYNCRO_BURST = 180.0

# Huntress Constants
HUNTRESS_API_URL = "https://api.huntress.io/v1/agents"
HUNTRESS_RATE_LIMIT = 60.0  # requests per second
