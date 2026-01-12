import pytest
import responses
from requests.exceptions import HTTPError, RetryError

from api.client import HuntressClient
from const import HUNTRESS_API_URL


@pytest.fixture
def huntress_client(mock_settings):
    client = HuntressClient(
        api_key=mock_settings["HuntressAPIKey"],
        secret_key=mock_settings["huntressApiSecretKey"],
    )
    return client


class TestGetAgents:
    @responses.activate
    def test_returns_agents_list(self, huntress_client, sample_huntress_agents):
        """Test that get_agents returns the agents list."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": sample_huntress_agents},
            status=200,
        )

        result = huntress_client.get_agents()

        assert result == sample_huntress_agents
        assert len(result) == 4

    @responses.activate
    def test_pagination_params(self, huntress_client):
        """Test that page and limit parameters are passed correctly."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": []},
            status=200,
        )

        huntress_client.get_agents(page=2, limit=100)

        request_url = responses.calls[0].request.url
        assert "page=2" in request_url
        assert "limit=100" in request_url

    @responses.activate
    def test_auth_headers(self, huntress_client):
        """Test that Basic Auth header is present."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": []},
            status=200,
        )

        huntress_client.get_agents()

        assert "Authorization" in responses.calls[0].request.headers
        assert responses.calls[0].request.headers["Authorization"].startswith("Basic ")


class TestGetAgentsErrorHandling:
    @responses.activate
    def test_raises_http_error_on_401(self, huntress_client):
        """Test that 401 response raises HTTPError."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(HTTPError) as exc_info:
            huntress_client.get_agents()
        assert exc_info.value.response.status_code == 401

    @responses.activate
    def test_raises_retry_error_on_500(self, huntress_client):
        """Test that 500 response raises RetryError."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            body="Internal Server Error",
            status=500,
        )

        with pytest.raises(RetryError):
            huntress_client.get_agents()

    @responses.activate
    def test_raises_value_error_on_missing_agents_key(self, huntress_client):
        """Test that missing 'agents' key raises ValueError."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"data": []},
            status=200,
        )

        with pytest.raises(ValueError) as exc_info:
            huntress_client.get_agents()
        assert "agents" in str(exc_info.value).lower()

    @responses.activate
    def test_raises_value_error_on_malformed_json(self, huntress_client):
        """Test that malformed JSON raises ValueError."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            body="not valid json",
            status=200,
            content_type="application/json",
        )

        with pytest.raises(ValueError) as exc_info:
            huntress_client.get_agents()
        assert "json" in str(exc_info.value).lower()
