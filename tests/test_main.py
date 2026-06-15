import sys
from unittest.mock import Mock, patch

from main import _apply_filters, main
from services.comparison import ComparisonRow


class TestMain:
    @patch("main.SyncroClient")
    @patch("main.HuntressClient")
    @patch("main.ComparisonService")
    @patch("main.load_settings")
    @patch("main.console")  # Patch global console
    def test_main_cli_success(
        self,
        mock_console,
        mock_settings,
        mock_service_cls,
        mock_huntress,
        mock_syncro,
    ):
        """Test successful CLI execution."""
        mock_settings.return_value = {
            "SyncroAPIKey": "key",
            "SyncroSubDomain": "sub",
            "HuntressAPIKey": "h_key",
            "HuntressSecretKey": "h_secret",
        }

        # Mock service return
        mock_result = Mock()
        mock_result.rows = [ComparisonRow("A", "B", "OK!", "Acme")]
        mock_result.syncro_count = 1
        mock_result.huntress_count = 1
        mock_result.syncro_assets = []
        mock_result.huntress_agents = []

        mock_service_cls.return_value.fetch_and_compare.return_value = mock_result

        test_args = ["main.py", "--compare", "--output", "out.csv"]
        with patch.object(sys, "argv", test_args):
            main()

        mock_service_cls.return_value.fetch_and_compare.assert_called_once()
        assert any(
            "Results written to" in str(c) for c in mock_console.print.mock_calls
        )

    @patch("main.create_parser")
    def test_main_shows_help_no_args(self, mock_parser_func):
        """Test that help is shown when no arguments provided."""
        mock_parser = Mock()
        mock_parser_func.return_value = mock_parser
        mock_parser.parse_args.return_value = Mock(compare=False)

        main()

        mock_parser.print_help.assert_called_once()


class TestApplyFilters:
    def _args(self, org=None, exclude_org=None, show_ignored=False):
        return Mock(
            org=org or [],
            exclude_org=exclude_org or [],
            show_ignored=show_ignored,
        )

    def _rows(self):
        return [
            ComparisonRow("PC-1", "PC-1", "OK!", organization="Acme"),
            ComparisonRow("PC-2", "", "Missing in Huntress", organization="Globex"),
            ComparisonRow("OLD-PC", "OLD-PC", "OK!", organization="Acme"),
        ]

    def test_include_only_org(self):
        rows, _ = _apply_filters(self._rows(), self._args(org=["Acme"]), {})
        assert {r.organization for r in rows} == {"Acme"}
        assert len(rows) == 2

    def test_exclude_org_from_args_and_settings(self):
        rows, _ = _apply_filters(
            self._rows(),
            self._args(exclude_org=["Globex"]),
            {"ExcludedOrganizations": ["Acme"]},
        )
        assert rows == []

    def test_ignored_hidden_by_default(self):
        settings = {"IgnoredAssets": ["old-pc"]}
        rows, ignored = _apply_filters(self._rows(), self._args(), settings)
        assert all(r.syncro_name != "OLD-PC" for r in rows)
        assert ignored == {"old-pc"}

    def test_show_ignored_keeps_them(self):
        settings = {"IgnoredAssets": ["old-pc"]}
        rows, _ = _apply_filters(self._rows(), self._args(show_ignored=True), settings)
        assert any(r.syncro_name == "OLD-PC" for r in rows)
