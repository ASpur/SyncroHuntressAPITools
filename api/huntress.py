from typing import Dict, List
from requests.auth import HTTPBasicAuth
from api.base import BaseClient
from utils.rate_limit import RateLimiter

# Rate limiting: 60 requests per second
_rate_limiter = RateLimiter(rate=60.0, name="Huntress API")
_client = BaseClient(rate_limiter=_rate_limiter)

def get_agents(settings: Dict, page: int = 1, limit: int = 500) -> List[Dict]:
    """Get Huntress agents."""
    url = "https://api.huntress.io/v1/agents"
    
    auth = HTTPBasicAuth(settings['HuntressAPIKey'], settings['huntressApiSecretKey'])
    params = {"page": page, "limit": limit}

    response = _client.request("GET", url, auth=auth, params=params)
    try:
        data = response.json()
    except Exception as e:
        raise ValueError(f"Failed to parse JSON response: {e}")

    if "agents" not in data:
        raise ValueError("API response missing 'agents' key")

    return data["agents"]