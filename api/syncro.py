from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from api.base import BaseClient
from utils.rate_limit import RateLimiter

# Rate limiting: 180 requests per minute = 3 requests per second
_rate_limiter = RateLimiter(rate=3.0, burst=180.0, name="Syncro API")
_client = BaseClient(rate_limiter=_rate_limiter)


def _make_request(settings: Dict, endpoint: str, params: Optional[Dict] = None) -> Dict:
    """Make a request to the Syncro API."""
    base_url = f"https://{settings['SyncroSubDomain']}.syncromsp.com/api/v1/{endpoint}"

    # Add API key to params
    if params is None:
        params = {}
    params["api_key"] = settings["SyncroAPIKey"]

    response = _client.request(
        "GET", base_url, params=params, headers={"Accept": "application/json"}
    )
    try:
        data = response.json()
    except Exception as e:
        raise ValueError(f"Failed to parse JSON response: {e}")
    return data


def get_tickets(settings: Dict, page: int = 1, open_only: bool = False) -> List[Dict]:
    """Get Syncro tickets."""
    params = {"page": page}
    if open_only:
        params["status"] = "Not Closed"

    data = _make_request(settings, "tickets", params)
    return data.get("tickets", [])


def get_assets(settings: Dict, page: int = 1) -> List[Dict]:
    """Get Syncro assets for a single page."""
    params = {"page": page}
    data = _make_request(settings, "customer_assets", params)
    return data.get("assets", [])


def _get_total_pages(settings: Dict) -> int:
    """Get total number of asset pages from API metadata."""
    try:
        data = _make_request(settings, "customer_assets", {"page": 1})
        return data.get("meta", {}).get("total_pages", 1)
    except Exception:
        return 1


def get_all_assets(settings: Dict, max_pages: int = 50) -> List[Dict]:
    """Get all Syncro assets across multiple pages using parallel requests."""
    total_pages = min(_get_total_pages(settings), max_pages)

    if total_pages <= 1:
        return get_assets(settings, page=1)

    assets = []
    with ThreadPoolExecutor(max_workers=min(total_pages, 10)) as executor:
        futures = {
            executor.submit(get_assets, settings, page): page
            for page in range(1, total_pages + 1)
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                assets.extend(result)
            except Exception as e:
                print(f"Failed to fetch page: {e}")

    return assets
