import logging
import time
from typing import Dict, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

class BaseClient:
    """Base client for API interactions with common functionality."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.session = requests.Session()
        self._configure_retries()
        self.rate_limiter = rate_limiter

    def _configure_retries(self):
        """Configure automatic retries for the session."""
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an HTTP request with rate limiting and error handling."""
        if self.rate_limiter:
            self.rate_limiter.acquire()

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
