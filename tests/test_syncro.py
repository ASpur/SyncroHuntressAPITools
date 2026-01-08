import pytest
import responses
from requests.exceptions import HTTPError
from api import syncro


class TestGetAssets:
    @responses.activate
    def test_returns_assets_list(self, mock_settings, sample_syncro_assets):
        """Test that get_assets returns the assets list from API response."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": sample_syncro_assets},
            status=200,
        )

        result = syncro.get_assets(mock_settings)

        assert result == sample_syncro_assets
        assert len(result) == 4

    @responses.activate
    def test_includes_api_key(self, mock_settings):
        """Test that request includes API key in query params."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        syncro.get_assets(mock_settings)

        request_url = responses.calls[0].request.url
        assert "api_key=fake-syncro-api-key" in request_url

    @responses.activate
    def test_pagination(self, mock_settings):
        """Test that page parameter is included."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        syncro.get_assets(mock_settings, page=3)

        request_url = responses.calls[0].request.url
        assert "page=3" in request_url


class TestGetAllAssets:
    @responses.activate
    def test_fetches_multiple_pages(self, mock_settings):
        """Test that get_all_assets fetches until empty page."""
        page1_assets = [{"id": 1, "name": "Asset1"}]
        page2_assets = [{"id": 2, "name": "Asset2"}]

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
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        result = syncro.get_all_assets(mock_settings)

        assert len(result) == 2
        assert result[0]["name"] == "Asset1"
        assert result[1]["name"] == "Asset2"

    @responses.activate
    def test_respects_max_pages(self, mock_settings):
        """Test that get_all_assets stops at max_pages."""
        for _ in range(5):
            responses.add(
                responses.GET,
                "https://testcompany.syncromsp.com/api/v1/customer_assets",
                json={"assets": [{"id": 1, "name": "Asset"}]},
                status=200,
            )

        syncro.get_all_assets(mock_settings, max_pages=3)

        assert len(responses.calls) == 3


class TestGetTickets:
    @responses.activate
    def test_returns_tickets_list(self, mock_settings, sample_syncro_tickets):
        """Test that get_tickets returns the tickets list."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/tickets",
            json={"tickets": sample_syncro_tickets},
            status=200,
        )

        result = syncro.get_tickets(mock_settings)

        assert result == sample_syncro_tickets

    @responses.activate
    def test_open_only_filter(self, mock_settings):
        """Test that open_only adds status filter."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/tickets",
            json={"tickets": []},
            status=200,
        )

        syncro.get_tickets(mock_settings, open_only=True)

        request_url = responses.calls[0].request.url
        assert "status=Not%20Closed" in request_url


class TestSyncroErrorHandling:
    @responses.activate
    def test_get_assets_raises_http_error_on_401(self, mock_settings):
        """Test that 401 response raises HTTPError."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(HTTPError) as exc_info:
            syncro.get_assets(mock_settings)
        assert exc_info.value.response.status_code == 401

    @responses.activate
    def test_get_assets_raises_http_error_on_500(self, mock_settings):
        """Test that 500 response raises HTTPError."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            body="Internal Server Error",
            status=500,
        )

        with pytest.raises(HTTPError) as exc_info:
            syncro.get_assets(mock_settings)
        assert exc_info.value.response.status_code == 500

    @responses.activate
    def test_get_assets_raises_value_error_on_missing_key(self, mock_settings):
        """Test that missing 'assets' key raises ValueError with clear message."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"data": []},  # Wrong key
            status=200,
        )

        with pytest.raises(ValueError) as exc_info:
            syncro.get_assets(mock_settings)
        assert "assets" in str(exc_info.value).lower()

    @responses.activate
    def test_get_tickets_raises_value_error_on_missing_key(self, mock_settings):
        """Test that missing 'tickets' key raises ValueError with clear message."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/tickets",
            json={"data": []},  # Wrong key
            status=200,
        )

        with pytest.raises(ValueError) as exc_info:
            syncro.get_tickets(mock_settings)
        assert "tickets" in str(exc_info.value).lower()

    @responses.activate
    def test_get_assets_raises_value_error_on_malformed_json(self, mock_settings):
        """Test that malformed JSON raises ValueError with clear message."""
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            body="not valid json{",
            status=200,
            content_type="application/json",
        )

        with pytest.raises(ValueError) as exc_info:
            syncro.get_assets(mock_settings)
        assert "json" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()
