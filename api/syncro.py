import requests
from requests.exceptions import JSONDecodeError
from requests.models import Response
from typing import Dict, List, Optional
from utils.rate_limit import RateLimiter

# Rate limiting: 180 requests per minute = 3 requests per second
# Burst of 180 allows all requests in a minute window to fire instantly
_rate_limiter = RateLimiter(rate=3.0, burst=180.0, name="Syncro API")


def _make_request(settings: Dict, endpoint: str, paths: Optional[List[str]] = None) -> Response:
    """Make a request to the Syncro API."""
    if paths is None:
        paths = []

    _rate_limiter.acquire()

    base_url = f"https://{settings['SyncroSubDomain']}.syncromsp.com/api/v1/"
    request_url = f"{base_url}{endpoint}?api_key={settings['SyncroAPIKey']}"

    for path in paths:
        request_url += f"&{path}"

    response = requests.get(request_url, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response


def _parse_response(response: Response, key: str) -> List[Dict]:
    """Parse JSON response and extract the specified key."""
    try:
        data = response.json()
    except JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}")

    if key not in data:
        raise ValueError(f"API response missing '{key}' key")

    return data[key]


def get_tickets(settings: Dict, page: int = 1, open_only: bool = False) -> List[Dict]:
    """Get Syncro tickets."""
    paths = [f"page={page}"]

    if open_only:
        paths.append("status=Not%20Closed")

    response = _make_request(settings, "tickets", paths)
    return _parse_response(response, "tickets")


def get_assets(settings: Dict, page: int = 1) -> List[Dict]:
    """Get Syncro assets for a single page."""
    paths = [f"page={page}"]
    response = _make_request(settings, "customer_assets", paths)
    return _parse_response(response, "assets")


def _get_total_pages(settings: Dict) -> int:
    """Get total number of asset pages from API metadata."""
    paths = ["page=1"]
    response = _make_request(settings, "customer_assets", paths)
    try:
        data = response.json()
        return data.get("meta", {}).get("total_pages", 1)
    except JSONDecodeError:
        return 1


def get_all_assets(settings: Dict, max_pages: int = 50) -> List[Dict]:
    """Get all Syncro assets across multiple pages using parallel requests."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Get total pages from API metadata
    total_pages = min(_get_total_pages(settings), max_pages)

    if total_pages <= 1:
        return get_assets(settings, page=1)

    # Fetch all pages in parallel - rate limiter handles the throttling
    assets = []
    with ThreadPoolExecutor(max_workers=total_pages) as executor:
        futures = {
            executor.submit(get_assets, settings, page): page
            for page in range(1, total_pages + 1)
        }
        for future in as_completed(futures):
            assets.extend(future.result())

    return assets