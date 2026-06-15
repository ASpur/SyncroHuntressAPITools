from unittest.mock import Mock

import pytest

from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
from services.comparison import ComparisonService, extract_org, normalize


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
        huntress.get_all_agents.return_value = [{"hostname": "WORKSTATION-001"}]

        result = service.fetch_and_compare(mismatches_first=True)

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_OK
        assert result.syncro_count == 1
        assert result.huntress_count == 1

    def test_identifies_missing_in_huntress(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "ORPHAN-PC"}]
        huntress.get_all_agents.return_value = []

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_MISSING_HUNTRESS

    def test_identifies_missing_in_syncro(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = []
        huntress.get_all_agents.return_value = [{"hostname": "GHOST-PC"}]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_MISSING_SYNCRO

    def test_case_insensitive_matching(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "Workstation-001"}]
        huntress.get_all_agents.return_value = [{"hostname": "WORKSTATION-001"}]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_OK

    def test_duplicate_hostnames_grouped(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [{"name": "Workstation-001"}]
        huntress.get_all_agents.return_value = [
            {"hostname": "WORKSTATION-001"},
            {"hostname": "workstation-001"},
        ]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_OK
        # Should count unique normalized assets
        assert result.huntress_count == 1

    def test_sorts_mismatches_last(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [
            {"name": "OK-PC"},
            {"name": "MISSING-IN-HUNTRESS"},
        ]
        huntress.get_all_agents.return_value = [{"hostname": "OK-PC"}]

        result = service.fetch_and_compare(mismatches_first=False)

        assert len(result.rows) == 2
        # OK-PC should be first (bottom if first means 0 index?)
        # Logic: 0 if OK else 1. So OK sorts first (0 < 1).
        assert result.rows[0].syncro_name == "OK-PC"
        assert result.rows[0].status == STATUS_OK

        assert result.rows[1].syncro_name == "MISSING-IN-HUNTRESS"
        assert result.rows[1].status == STATUS_MISSING_HUNTRESS

    def test_assets_with_empty_names_ignored(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [
            {"name": ""},
            {"name": None},
            {"name": "VALID-PC"},
        ]
        huntress.get_all_agents.return_value = [
            {"hostname": ""},
            {"hostname": None},
            {"hostname": "VALID-PC"},
        ]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_OK


class TestExtractOrg:
    def test_reads_business_name(self):
        asset = {"name": "PC", "customer": {"business_name": "Acme Corp"}}
        assert extract_org(asset) == "Acme Corp"

    def test_falls_back_to_business_and_full_name(self):
        asset = {"customer": {"business_and_full_name": "Acme (Jane Doe)"}}
        assert extract_org(asset) == "Acme (Jane Doe)"

    def test_returns_empty_when_no_customer(self):
        assert extract_org({"name": "PC"}) == ""


class TestOrganizationOnRows:
    @pytest.fixture
    def mock_clients(self):
        return Mock(), Mock()

    @pytest.fixture
    def service(self, mock_clients):
        return ComparisonService(mock_clients[0], mock_clients[1])

    def test_org_populated_for_syncro_side(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [
            {"name": "WS-1", "customer": {"business_name": "Acme Corp"}}
        ]
        huntress.get_all_agents.return_value = [{"hostname": "WS-1"}]

        result = service.fetch_and_compare()

        assert result.rows[0].organization == "Acme Corp"

    def test_org_blank_for_huntress_only_row(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = []
        huntress.get_all_agents.return_value = [{"hostname": "GHOST-PC"}]

        result = service.fetch_and_compare()

        assert result.rows[0].status == STATUS_MISSING_SYNCRO
        assert result.rows[0].organization == ""

    def test_org_filled_from_huntress_when_no_syncro(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = []
        huntress.get_all_agents.return_value = [
            {"hostname": "GHOST-PC", "organization_id": 42}
        ]
        huntress.get_all_organizations.return_value = [
            {"id": 42, "name": "Huntress Org"}
        ]

        result = service.fetch_and_compare()

        assert result.rows[0].status == STATUS_MISSING_SYNCRO
        assert result.rows[0].organization == "Huntress Org"

    def test_syncro_org_preferred_over_huntress(self, service, mock_clients):
        syncro, huntress = mock_clients
        syncro.get_all_assets.return_value = [
            {"name": "WS-1", "customer": {"business_name": "Syncro Co"}}
        ]
        huntress.get_all_agents.return_value = [
            {"hostname": "WS-1", "organization_id": 7}
        ]
        huntress.get_all_organizations.return_value = [{"id": 7, "name": "Huntress Co"}]

        result = service.fetch_and_compare()

        assert result.rows[0].status == STATUS_OK
        assert result.rows[0].organization == "Syncro Co"


class TestNetBiosTruncationMatching:
    """Regression guard: Syncro stores NetBIOS-truncated (15-char) names while
    Huntress stores full hostnames. Truncated matching must treat them as the
    same machine. Captured from real data during Phase 0."""

    @pytest.fixture
    def service(self):
        return ComparisonService(Mock(), Mock())

    @pytest.mark.parametrize(
        "syncro_name,huntress_name",
        [
            ("ORINLAW-TERRAHL", "OrinLaw-TerrahLaptop"),
            ("PCHSRESEARCHLAP", "PCHSResearchLaptop"),
            ("SBP-SOUTHBEND-U", "SBP-SOUTHBEND-USR-01"),
        ],
    )
    def test_truncated_syncro_name_matches_full_hostname(
        self, service, syncro_name, huntress_name
    ):
        service.syncro_client.get_all_assets.return_value = [{"name": syncro_name}]
        service.huntress_client.get_all_agents.return_value = [
            {"hostname": huntress_name}
        ]

        result = service.fetch_and_compare()

        assert len(result.rows) == 1
        assert result.rows[0].status == STATUS_OK
