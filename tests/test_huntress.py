import pytest
import responses
from requests.exceptions import HTTPError
from api import huntress


class TestGetAgents:
    @responses.activate
    def test_returns_agents_list(self, mock_settings, sample_huntress_agents):
        """Test that get_agents returns the agents list from API response."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": sample_huntress_agents},
            status=200,
        )

        result = huntress.get_agents(mock_settings)

        assert result == sample_huntress_agents
        assert len(result) == 4

    @responses.activate
    def test_uses_basic_auth(self, mock_settings):
        """Test that request includes Basic auth header."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": []},
            status=200,
        )

        huntress.get_agents(mock_settings)

        assert len(responses.calls) == 1
        auth_header = responses.calls[0].request.headers["Authorization"]
        assert auth_header.startswith("Basic ")

    @responses.activate
    def test_pagination_params(self, mock_settings):
        """Test that page and limit parameters are included in URL."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": []},
            status=200,
        )

        huntress.get_agents(mock_settings, page=2, limit=100)

        request_url = responses.calls[0].request.url
        assert "page=2" in request_url
        assert "limit=100" in request_url

    @responses.activate
    def test_default_pagination(self, mock_settings):
        """Test default pagination values."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": []},
            status=200,
        )

        huntress.get_agents(mock_settings)

        request_url = responses.calls[0].request.url
        assert "page=1" in request_url
        assert "limit=500" in request_url


class TestGetAgentsErrorHandling:
    @responses.activate
    def test_raises_http_error_on_401(self, mock_settings):
        """Test that 401 response raises HTTPError."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(HTTPError) as exc_info:
            huntress.get_agents(mock_settings)
        assert exc_info.value.response.status_code == 401

    @responses.activate
    def test_raises_http_error_on_500(self, mock_settings):
        """Test that 500 response raises HTTPError."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            body="Internal Server Error",
            status=500,
        )

        with pytest.raises(HTTPError) as exc_info:
            huntress.get_agents(mock_settings)
        assert exc_info.value.response.status_code == 500

    @responses.activate
    def test_raises_value_error_on_missing_agents_key(self, mock_settings):
        """Test that missing 'agents' key raises ValueError with clear message."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"data": []},  # Wrong key
            status=200,
        )

        with pytest.raises(ValueError) as exc_info:
            huntress.get_agents(mock_settings)
        assert "agents" in str(exc_info.value).lower()

    @responses.activate
    def test_raises_value_error_on_malformed_json(self, mock_settings):
        """Test that malformed JSON raises ValueError with clear message."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            body="not valid json{",
            status=200,
            content_type="application/json",
        )

        with pytest.raises(ValueError) as exc_info:
            huntress.get_agents(mock_settings)
        assert "json" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


class TestHuntressRateLimiting:
    @responses.activate
    def test_rate_limiter_allows_burst_within_limit(self, mock_settings):
        """Test that bursts within rate limit complete quickly (token bucket)."""
        import time
        from api.huntress import _rate_limiter

        # Reset the rate limiter to full tokens
        _rate_limiter.tokens = _rate_limiter.max_tokens
        _rate_limiter.last_refill = time.time()

        # Add mock responses for 5 requests (well within burst limit of 60 tokens)
        for _ in range(5):
            responses.add(
                responses.GET,
                "https://api.huntress.io/v1/agents",
                json={"agents": []},
                status=200,
            )

        start_time = time.time()
        for _ in range(5):
            huntress.get_agents(mock_settings)
        elapsed = time.time() - start_time

        # Burst of 5 requests should complete very quickly (under 0.1s)
        assert elapsed < 0.1, f"Burst requests too slow ({elapsed:.3f}s), token bucket may not be working"

    @responses.activate
    def test_rate_limiter_enforces_limit_when_exhausted(self, mock_settings):
        """Test that rate limiter waits when tokens exhausted."""
        import time
        from api.huntress import _rate_limiter

        # Exhaust the tokens
        _rate_limiter.tokens = 0
        _rate_limiter.last_refill = time.time()

        # Add mock responses
        for _ in range(2):
            responses.add(
                responses.GET,
                "https://api.huntress.io/v1/agents",
                json={"agents": []},
                status=200,
            )

        start_time = time.time()
        for _ in range(2):
            huntress.get_agents(mock_settings)
        elapsed = time.time() - start_time

        # With 0 tokens, need to wait for refill (~0.017s per token at 60/sec)
        assert elapsed >= 0.01, f"Requests completed too fast ({elapsed:.3f}s), rate limiting may not be working"
