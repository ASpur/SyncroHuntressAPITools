import responses
from unittest.mock import patch
from io import StringIO

from services.comparison import normalize, compare_agents


class TestNormalize:
    def test_basic_normalization(self):
        """Test basic string normalization."""
        assert normalize("WORKSTATION-001") == "workstation-001"

    def test_truncates_to_length(self):
        """Test that names are truncated to specified length."""
        assert normalize("VERYLONGWORKSTATIONNAME", length=10) == "verylongwo"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize("  WORKSTATION  ") == "workstation"

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        assert normalize("") is None

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert normalize(None) is None

    def test_default_length(self):
        """Test default length of 15 characters."""
        result = normalize("12345678901234567890")
        assert len(result) == 15


class TestCompareAgents:
    @responses.activate
    def test_identifies_matching_agents(self, mock_settings):
        """Test that matching agents are identified correctly."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": [{"hostname": "WORKSTATION-001"}]},
            status=200,
        )
        # First call for metadata
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "WORKSTATION-001"}], "meta": {"total_pages": 1}},
            status=200,
        )
        # Second call for actual page fetch
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "WORKSTATION-001"}]},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        assert "OK!" in result

    @responses.activate
    def test_identifies_missing_in_huntress(self, mock_settings):
        """Test that assets missing in Huntress are identified."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": []},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "ORPHAN-PC"}], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "ORPHAN-PC"}]},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        assert "Missing in Huntress" in result

    @responses.activate
    def test_identifies_missing_in_syncro(self, mock_settings):
        """Test that agents missing in Syncro are identified."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": [{"hostname": "GHOST-PC"}]},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        assert "Missing in Syncro" in result

    @responses.activate
    def test_case_insensitive_matching(self, mock_settings):
        """Test that matching is case-insensitive."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": [{"hostname": "workstation-001"}]},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "WORKSTATION-001"}], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "WORKSTATION-001"}]},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        assert "OK!" in result

    @responses.activate
    def test_writes_csv_output(self, mock_settings, tmp_path):
        """Test that CSV output is written correctly."""
        output_file = tmp_path / "output.csv"

        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": [{"hostname": "PC-001"}]},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "PC-001"}], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "PC-001"}]},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()):
            compare_agents(mock_settings, output_file=str(output_file), use_color=False)

        assert output_file.exists()
        content = output_file.read_text()
        assert "Syncro Asset" in content
        assert "PC-001" in content

    @responses.activate
    def test_empty_results_from_both_apis(self, mock_settings):
        """Test behavior when both APIs return empty results."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": []},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": []},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        # Should only have header and separator, no data rows
        lines = [l for l in result.strip().split("\n") if l]
        assert len(lines) == 2  # Header + separator

    @responses.activate
    def test_duplicate_hostnames_grouped(self, mock_settings):
        """Test that duplicate normalized names are grouped together."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": [
                {"hostname": "WORKSTATION-001"},
                {"hostname": "workstation-001"},  # Same when normalized
            ]},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "Workstation-001"}], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [{"name": "Workstation-001"}]},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        # Should show OK since all normalize to the same key
        assert "OK!" in result
        # Should only have one data row (plus header and separator)
        lines = [l for l in result.strip().split("\n") if l]
        assert len(lines) == 3

    @responses.activate
    def test_assets_with_empty_names_ignored(self, mock_settings):
        """Test that assets with empty or None names are ignored."""
        responses.add(
            responses.GET,
            "https://api.huntress.io/v1/agents",
            json={"agents": [
                {"hostname": ""},
                {"hostname": None},
                {"hostname": "VALID-PC"},
            ]},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [
                {"name": ""},
                {"name": None},
                {"name": "VALID-PC"},
            ], "meta": {"total_pages": 1}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://testcompany.syncromsp.com/api/v1/customer_assets",
            json={"assets": [
                {"name": ""},
                {"name": None},
                {"name": "VALID-PC"},
            ]},
            status=200,
        )

        with patch("sys.stdout", new=StringIO()) as output:
            compare_agents(mock_settings, use_color=False)
            result = output.getvalue()

        # Should only match VALID-PC, empty/None should be ignored
        assert "OK!" in result
        assert result.count("Missing") == 0
