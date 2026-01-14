import pytest
from unittest.mock import patch, Mock
import sys
from main import main, create_parser

class TestMain:
    @patch("main.SyncroClient")
    @patch("main.HuntressClient")
    @patch("main.ComparisonService")
    @patch("main.load_settings")
    @patch("main.console") # Patch global console
    def test_main_cli_success(self, mock_console, mock_settings, mock_service_cls, mock_huntress, mock_syncro):
        """Test successful CLI execution."""
        mock_settings.return_value = {
            "SyncroAPIKey": "key", 
            "SyncroSubDomain": "sub",
            "HuntressAPIKey": "h_key",
            "HuntressSecretKey": "h_secret"
        }
        
        # Mock service return
        mock_result = Mock()
        mock_result.rows = [("A", "B", "OK")]
        mock_result.syncro_count = 1
        mock_result.huntress_count = 1
        mock_result.syncro_assets = []
        mock_result.huntress_agents = []
        
        mock_service_cls.return_value.fetch_and_compare.return_value = mock_result
        
        # Run with arguments
        test_args = ["main.py", "--compare", "--output", "out.csv"]
        with patch.object(sys, "argv", test_args):
            main()
            
        mock_service_cls.return_value.fetch_and_compare.assert_called_once()
        # Verify output message
        assert any("Results written to" in str(c) for c in mock_console.print.mock_calls)

    @patch("main.create_parser")
    def test_main_shows_help_no_args(self, mock_parser_func):
        """Test that help is shown when no arguments provided."""
        mock_parser = Mock()
        mock_parser_func.return_value = mock_parser
        mock_parser.parse_args.return_value = Mock(compare=False)
        
        main()
        
        mock_parser.print_help.assert_called_once()
