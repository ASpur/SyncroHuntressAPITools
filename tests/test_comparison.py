from unittest.mock import Mock

import pytest

from services.comparison import ComparisonService, normalize


class TestNormalize:
    def test_basic_normalization(self):
        assert normalize("WORKSTATION-001") == "workstation-001"

    def test_truncates_to_length(self):
        assert normalize("VERYLONGWORKSTATIONNAME", length=10) == "verylongwo"

    def test_strips_whitespace(self):
        assert normalize("  WORKSTATION  ") == "workstation"

    def test_empty_string_returns_none(self):
        assert normalize("") is None

    def test_none_returns_none(self):
        assert normalize(None) is None


class TestComparisonService:
    @pytest.fixture
    def mock_clients(self):
        syncro = Mock()
        huntress = Mock()
        return syncro, huntress

    @pytest.fixture
    def service(self, mock_clients):
        return ComparisonService(mock_clients[0], mock_clients[1])

    def test_identifies_matching_agents(self, service, mock_clients):
        """Test that matching agents are identified correctly."""
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "WORKSTATION-001"}]
        huntress.get_agents.return_value = [{"hostname": "WORKSTATION-001"}]

        result = service.fetch_and_compare(mismatches_first=True)

        assert len(result.rows) == 1
        assert result.rows[0][2] == "OK!"
        assert result.syncro_count == 1
        assert result.huntress_count == 1

    def test_identifies_missing_in_huntress(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "ORPHAN-PC"}]
        huntress.get_agents.return_value = []

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0][2] == "Missing in Huntress"

    def test_identifies_missing_in_syncro(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = []
        huntress.get_agents.return_value = [{"hostname": "GHOST-PC"}]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0][2] == "Missing in Syncro"

    def test_case_insensitive_matching(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "Workstation-001"}]
        huntress.get_agents.return_value = [{"hostname": "WORKSTATION-001"}]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0][2] == "OK!"

    def test_duplicate_hostnames_grouped(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "Workstation-001"}]
        huntress.get_agents.return_value = [
            {"hostname": "WORKSTATION-001"},
            {"hostname": "workstation-001"},
        ]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0][2] == "OK!"
        # Should count unique normalized assets
        assert result.huntress_count == 1

    def test_sorts_mismatches_last(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [
            {"name": "OK-PC"},
            {"name": "MISSING-IN-HUNTRESS"}
        ]
        huntress.get_agents.return_value = [{"hostname": "OK-PC"}]

        result = service.fetch_and_compare(mismatches_first=False)

        assert len(result.rows) == 2
        # OK-PC should be first (bottom if first means 0 index?)
        # Logic: 0 if OK else 1. So OK sorts first (0 < 1).
        assert result.rows[0][0] == "OK-PC"
        assert result.rows[0][2] == "OK!"
        
        assert result.rows[1][0] == "MISSING-IN-HUNTRESS"
        assert result.rows[1][2] == "Missing in Huntress"

    def test_assets_with_empty_names_ignored(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [
            {"name": ""},
            {"name": None},
            {"name": "VALID-PC"},
        ]
        huntress.get_agents.return_value = [
            {"hostname": ""},
            {"hostname": None},
            {"hostname": "VALID-PC"},
        ]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0][2] == "OK!"
