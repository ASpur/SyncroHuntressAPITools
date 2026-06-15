import pytest
import responses
from requests.exceptions import HTTPError, RetryError

from api.client import HuntressClient
from const import HUNTRESS_API_URL, HUNTRESS_ORGANIZATIONS_URL


@pytest.fixture
def huntress_client(mock_settings):
    client = HuntressClient(
        api_key=mock_settings["HuntressAPIKey"],
        secret_key=mock_settings["HuntressSecretKey"],
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


class TestGetAllAgents:
    @responses.activate
    def test_fetches_multiple_pages(self, huntress_client):
        """Test that get_all_agents fetches all pages from pagination metadata.

        Huntress reports ``total_count`` and ``limit`` (no ``total_pages``), so
        the client must derive the page count: total_count=2 / limit=1 -> 2.
        """
        page1_agents = [{"id": 1, "hostname": "Agent1"}]
        page2_agents = [{"id": 2, "hostname": "Agent2"}]

        # First call: metadata probe; total_count=2 with limit=1 -> 2 pages.
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={
                "agents": page1_agents,
                "pagination": {"total_count": 2, "limit": 1},
            },
            status=200,
        )
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": page1_agents},
            status=200,
        )
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": page2_agents},
            status=200,
        )

        result = huntress_client.get_all_agents(limit=1)

        assert len(result) == 2

    @responses.activate
    def test_fetches_remainder_beyond_full_first_page(self, huntress_client):
        """Regression guard: a full first page must not hide trailing agents.

        Mirrors the live bug where 504 agents were silently truncated to 500
        because only one page (limit=500) was ever fetched.
        """
        first_page = [{"id": i, "hostname": f"Agent{i}"} for i in range(500)]
        last_page = [{"id": i, "hostname": f"Agent{i}"} for i in range(500, 504)]

        # Metadata probe: 504 total at limit 500 -> 2 pages.
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={
                "agents": first_page,
                "pagination": {"total_count": 504, "limit": 500},
            },
            status=200,
        )
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": first_page},
            status=200,
        )
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": last_page},
            status=200,
        )

        result = huntress_client.get_all_agents(limit=500)

        assert len(result) == 504

    @responses.activate
    def test_single_page(self, huntress_client):
        """Test that get_all_agents returns a single page without extra calls."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={
                "agents": [{"id": 1, "hostname": "Agent1"}],
                "pagination": {"total_count": 1, "limit": 500},
            },
            status=200,
        )

        result = huntress_client.get_all_agents()

        assert len(result) == 1
        # 1 metadata call + 1 page call = 2
        assert len(responses.calls) == 2

    @responses.activate
    def test_respects_max_pages(self, huntress_client):
        """Test that get_all_agents stops at max_pages even if API has more."""
        # total_count=10 at limit=1 -> 10 pages, but max_pages caps it at 3.
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": [{"id": 1}], "pagination": {"total_count": 10, "limit": 1}},
            status=200,
        )
        for _ in range(3):
            responses.add(
                responses.GET,
                HUNTRESS_API_URL,
                json={"agents": [{"id": 1, "hostname": "Agent"}]},
                status=200,
            )

        huntress_client.get_all_agents(limit=1, max_pages=3)

        # 1 metadata call + 3 page calls = 4
        assert len(responses.calls) == 4

    @responses.activate
    def test_passes_limit(self, huntress_client):
        """Test that the limit parameter is forwarded to page requests."""
        responses.add(
            responses.GET,
            HUNTRESS_API_URL,
            json={"agents": [], "pagination": {"total_count": 0, "limit": 500}},
            status=200,
        )

        huntress_client.get_all_agents(limit=500)

        assert "limit=500" in responses.calls[0].request.url


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


class TestGetOrganizations:
    @responses.activate
    def test_returns_organizations_list(self, huntress_client):
        """get_organizations returns the organizations list."""
        orgs = [{"id": 1, "name": "Acme"}, {"id": 2, "name": "Globex"}]
        responses.add(
            responses.GET,
            HUNTRESS_ORGANIZATIONS_URL,
            json={"organizations": orgs, "pagination": {"total_count": 2}},
            status=200,
        )

        result = huntress_client.get_organizations()

        assert result == orgs

    @responses.activate
    def test_raises_on_missing_key(self, huntress_client):
        responses.add(
            responses.GET,
            HUNTRESS_ORGANIZATIONS_URL,
            json={"pagination": {}},
            status=200,
        )

        with pytest.raises(ValueError):
            huntress_client.get_organizations()

    @responses.activate
    def test_get_all_organizations_paginates(self, huntress_client):
        """get_all_organizations fetches all pages from total_count/limit."""
        # First call (page-count probe) reports 2 pages worth (limit 500).
        responses.add(
            responses.GET,
            HUNTRESS_ORGANIZATIONS_URL,
            json={
                "organizations": [{"id": i, "name": f"Org{i}"} for i in range(500)],
                "pagination": {"total_count": 700, "limit": 500},
            },
            status=200,
        )
        responses.add(
            responses.GET,
            HUNTRESS_ORGANIZATIONS_URL,
            json={
                "organizations": [{"id": i, "name": f"Org{i}"} for i in range(500)],
                "pagination": {"total_count": 700, "limit": 500},
            },
            status=200,
        )
        responses.add(
            responses.GET,
            HUNTRESS_ORGANIZATIONS_URL,
            json={
                "organizations": [
                    {"id": i, "name": f"Org{i}"} for i in range(500, 700)
                ],
                "pagination": {"total_count": 700, "limit": 500},
            },
            status=200,
        )

        result = huntress_client.get_all_organizations()

        assert len(result) == 700
