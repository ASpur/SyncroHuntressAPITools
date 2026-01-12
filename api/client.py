from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from requests.auth import HTTPBasicAuth

from api.base import BaseClient
from const import (
    HUNTRESS_API_URL,
    HUNTRESS_RATE_LIMIT,
    SYNCRO_BASE_URL_TEMPLATE,
    SYNCRO_BURST,
    SYNCRO_RATE_LIMIT,
)
from utils.rate_limit import RateLimiter


class SyncroClient(BaseClient):
    """Client for interacting with the Syncro MSP API."""

    def __init__(self, api_key: str, subdomain: str):
        rate_limiter = RateLimiter(
            rate=SYNCRO_RATE_LIMIT, burst=SYNCRO_BURST, name="Syncro API"
        )
        super().__init__(rate_limiter=rate_limiter)
        self.api_key = api_key
        self.base_url = SYNCRO_BASE_URL_TEMPLATE.format(subdomain=subdomain)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Syncro API."""
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}
        params["api_key"] = self.api_key

        response = self.request(
            "GET", url, params=params, headers={"Accept": "application/json"}
        )
        try:
            data = response.json()
        except Exception as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        return data

    def get_tickets(self, page: int = 1, open_only: bool = False) -> List[Dict]:
        """Get Syncro tickets."""
        params = {"page": page}
        if open_only:
            params["status"] = "Not Closed"

        data = self._make_request("tickets", params)
        return data.get("tickets", [])

    def get_assets(self, page: int = 1) -> List[Dict]:
        """Get Syncro assets for a single page."""
        params = {"page": page}
        data = self._make_request("customer_assets", params)
        return data.get("assets", [])

    def _get_total_pages(self) -> int:
        """Get total number of asset pages from API metadata."""
        try:
            data = self._make_request("customer_assets", {"page": 1})
            return data.get("meta", {}).get("total_pages", 1)
        except Exception:
            return 1

    def get_all_assets(self, max_pages: int = 50) -> List[Dict]:
        """Get all Syncro assets across multiple pages using parallel requests."""
        total_pages = min(self._get_total_pages(), max_pages)

        if total_pages <= 1:
            return self.get_assets(page=1)

        assets = []
        with ThreadPoolExecutor(max_workers=min(total_pages, 10)) as executor:
            futures = {
                executor.submit(self.get_assets, page): page
                for page in range(1, total_pages + 1)
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    assets.extend(result)
                except Exception as e:
                    # In a real app we might want to log this or handle it
                    print(f"Failed to fetch page: {e}")

        return assets


class HuntressClient(BaseClient):
    """Client for interacting with the Huntress API."""

    def __init__(self, api_key: str, secret_key: str):
        rate_limiter = RateLimiter(rate=HUNTRESS_RATE_LIMIT, name="Huntress API")
        super().__init__(rate_limiter=rate_limiter)
        self.auth = HTTPBasicAuth(api_key, secret_key)

    def get_agents(self, page: int = 1, limit: int = 500) -> List[Dict]:
        """Get Huntress agents."""
        params = {"page": page, "limit": limit}

        response = self.request("GET", HUNTRESS_API_URL, auth=self.auth, params=params)
        try:
            data = response.json()
        except Exception as e:
            raise ValueError(f"Failed to parse JSON response: {e}")

        if "agents" not in data:
            raise ValueError("API response missing 'agents' key")

        return data["agents"]
