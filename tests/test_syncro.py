import pytest
import responses
from requests.exceptions import HTTPError, RetryError
from api.client import SyncroClient


@pytest.fixture
def syncro_client(mock_settings):
    return SyncroClient(
        api_key=mock_settings["SyncroAPIKey"],
        subdomain=mock_settings["SyncroSubDomain"],
    )


class TestGetAssets:
    @responses.activate
    def test_returns_assets_list(self, syncro_client, sample_syncro_assets):
        """Test that get_assets returns the assets list from API response."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": sample_syncro_assets},
            status=200,
        )

        result = syncro_client.get_assets()

        assert result == sample_syncro_assets
        assert len(result) == 4

    @responses.activate
    def test_includes_api_key(self, syncro_client):
        """Test that request includes API key in query params."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        syncro_client.get_assets()

        request_url = responses.calls[0].request.url
        assert "api_key=fake-syncro-api-key" in request_url

    @responses.activate
    def test_pagination(self, syncro_client):
        """Test that page parameter is included."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        syncro_client.get_assets(page=3)

        request_url = responses.calls[0].request.url
        assert "page=3" in request_url


class TestGetAllAssets:
    @responses.activate
    def test_fetches_multiple_pages(self, syncro_client):
        """Test that get_all_assets fetches all pages based on meta.total_pages."""
        page1_assets = [{"id": 1, "name": "Asset1"}]
        page2_assets = [{"id": 2, "name": "Asset2"}]

        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": page1_assets, "meta": {"total_pages": 2}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": page1_assets},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": page2_assets},
            status=200,
        )

        # We mock ThreadPoolExecutor if we wanted strict unit testing,
        # but integrations tests fine here
        result = syncro_client.get_all_assets()

        assert len(result) == 2

    @responses.activate
    def test_respects_max_pages(self, syncro_client):
        """Test that get_all_assets stops at max_pages even if API has more."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"id": 1}], "meta": {"total_pages": 5}},
            status=200,
        )
        for _ in range(3):
            responses.add(
                responses.GET,
                "https://testcompany.syncromsp.com/api/v1/customer_assets",
                json={"assets": [{"id": 1, "name": "Asset"}]},
                status=200,
            )

        syncro_client.get_all_assets(max_pages=3)

        # 1 metadata call + 3 page calls = 4
        assert len(responses.calls) == 4


class TestGetTickets:
    @responses.activate
    def test_returns_tickets_list(self, syncro_client, sample_syncro_tickets):
        """Test that get_tickets returns the tickets list."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/tickets",
            json={"tickets": sample_syncro_tickets},
            status=200,
        )

        result = syncro_client.get_tickets()

        assert result == sample_syncro_tickets

    @responses.activate
    def test_open_only_filter(self, syncro_client):
        """Test that open_only adds status filter."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/tickets",
            json={"tickets": []},
            status=200,
        )

        syncro_client.get_tickets(open_only=True)

        request_url = responses.calls[0].request.url
        assert "status=Not+Closed" in request_url


class TestSyncroErrorHandling:
    @responses.activate
    def test_get_assets_raises_http_error_on_401(self, syncro_client):
        """Test that 401 response raises HTTPError."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(HTTPError) as exc_info:
            syncro_client.get_assets()
        assert exc_info.value.response.status_code == 401

    @responses.activate
    def test_get_assets_raises_retry_error_on_500(self, syncro_client):
        """Test that 500 response raises RetryError (after retries)."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            body="Internal Server Error",
            status=500,
        )

        with pytest.raises(RetryError):
            syncro_client.get_assets()

    @responses.activate
    def test_get_assets_returns_empty_on_missing_key(self, syncro_client):
        """Test that missing 'assets' key returns empty list."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"data": []},
            status=200,
        )

        result = syncro_client.get_assets()
        assert result == []

    @responses.activate
    def test_get_assets_raises_value_error_on_malformed_json(self, syncro_client):
        """Test that malformed JSON raises ValueError."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            body="not valid json{",
            status=200,
            content_type="application/json",
        )

        with pytest.raises(ValueError) as exc_info:
            syncro_client.get_assets()
        assert "json" in str(exc_info.value).lower()
