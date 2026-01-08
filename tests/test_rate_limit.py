import time
import pytest
from utils.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_burst_up_to_rate(self):
        """Test that initial burst up to rate completes instantly."""
        limiter = RateLimiter(rate=10.0, name="Test")

        start = time.time()
        for _ in range(10):
            limiter.acquire()
        elapsed = time.time() - start

        # 10 requests with 10 tokens should be nearly instant
        assert elapsed < 0.1, f"Burst took too long: {elapsed:.3f}s"

    def test_waits_when_tokens_exhausted(self):
        """Test that limiter waits when tokens are exhausted."""
        limiter = RateLimiter(rate=10.0, name="Test")
        limiter.tokens = 0
        limiter.last_refill = time.time()

        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start

        # Should wait ~0.1s (1 token at 10/sec rate)
        assert elapsed >= 0.09, f"Did not wait long enough: {elapsed:.3f}s"

    def test_refills_tokens_over_time(self):
        """Test that tokens refill based on elapsed time."""
        limiter = RateLimiter(rate=10.0, name="Test")
        limiter.tokens = 0
        limiter.last_refill = time.time()

        # Wait for tokens to refill
        time.sleep(0.5)

        start = time.time()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.time() - start

        # After 0.5s at 10/sec, should have ~5 tokens, so 5 requests should be fast
        assert elapsed < 0.1, f"Requests after refill took too long: {elapsed:.3f}s"

    def test_thread_safety(self):
        """Test that rate limiter is thread-safe."""
        import threading

        limiter = RateLimiter(rate=100.0, name="Test")
        results = []

        def acquire_tokens():
            for _ in range(10):
                limiter.acquire()
                results.append(time.time())

        threads = [threading.Thread(target=acquire_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 50 results
        assert len(results) == 50
