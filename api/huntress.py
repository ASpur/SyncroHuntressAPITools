import base64
import requests
from requests.exceptions import JSONDecodeError
from typing import Dict, List
from utils.rate_limit import RateLimiter

# Rate limiting: 60 requests per second
_rate_limiter = RateLimiter(rate=60.0, name="Huntress API")


def get_agents(settings: Dict, page: int = 1, limit: int = 500) -> List[Dict]:
    """Get Huntress agents."""
    _rate_limiter.acquire()

    auth_string = f"{settings['HuntressAPIKey']}:{settings['huntressApiSecretKey']}"
    auth_bytes = auth_string.encode('utf-8')
    auth_encoded = base64.b64encode(auth_bytes).decode('utf-8')

    url = f"https://api.huntress.io/v1/agents?page={page}&limit={limit}"
    headers = {"Authorization": f"Basic {auth_encoded}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    try:
        data = response.json()
    except JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}")

    if "agents" not in data:
        raise ValueError("API response missing 'agents' key")

    return data["agents"]