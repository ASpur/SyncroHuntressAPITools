import requests
from requests.exceptions import JSONDecodeError
from requests.models import Response
from typing import Dict, List


def _make_request(settings: Dict, endpoint: str, paths: List[str] = None) -> Response:
    """Make a request to the Syncro API."""
    if paths is None:
        paths = []

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


def get_all_assets(settings: Dict, max_pages: int = 50) -> List[Dict]:
    """Get all Syncro assets across multiple pages."""
    assets = []
    for page in range(1, max_pages + 1):
        new_assets = get_assets(settings, page)
        if not new_assets:
            break
        assets.extend(new_assets)
    return assets