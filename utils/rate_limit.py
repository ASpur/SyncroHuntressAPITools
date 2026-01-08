import sys
import time
from threading import Lock


class RateLimiter:
    """Token bucket rate limiter that allows bursts while respecting rate limits.

    Args:
        rate: Maximum requests per second
        name: Name to display when rate limited (e.g., "Syncro API")
    """

    def __init__(self, rate: float, name: str = "API"):
        self.rate = rate
        self.name = name
        self.tokens = rate  # Start with full bucket
        self.max_tokens = rate  # Bucket size = 1 second worth of requests
        self.last_refill = time.time()
        self._lock = Lock()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def acquire(self):
        """Acquire a token, waiting if necessary."""
        with self._lock:
            self._refill()

            if self.tokens >= 1:
                self.tokens -= 1
                return

            # Calculate wait time
            wait_time = (1 - self.tokens) / self.rate
            sys.stdout.write(f"\r{self.name} rate limit reached, waiting {wait_time:.1f}s...")
            sys.stdout.flush()

            time.sleep(wait_time)

            # Clear the message
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()

            self._refill()
            self.tokens -= 1
