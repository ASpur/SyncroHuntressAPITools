from unittest.mock import Mock, patch
from PySide6.QtCore import QCoreApplication
import pytest
from gui.workers.comparison_worker import ComparisonWorker

@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app

class TestComparisonWorker:
    @pytest.fixture
    def mock_settings(self):
        return {
            "SyncroAPIKey": "syncro_key",
            "SyncroSubDomain": "syncro_sub",
            "HuntressAPIKey": "huntress_key",
            "HuntressSecretKey": "huntress_secret"
        }

    @pytest.fixture
    def worker(self, mock_settings, qapp):
        return ComparisonWorker(mock_settings)

    @patch("gui.workers.comparison_worker.SyncroClient")
    @patch("gui.workers.comparison_worker.HuntressClient")
    @patch("gui.workers.comparison_worker.ComparisonService")
    def test_run_success_emits_signals(self, mock_service_cls, mock_huntress_cls, mock_syncro_cls, worker):
        """Test that run executes successfully and emits results."""
        # Setup mocks
        mock_service = mock_service_cls.return_value
        result_mock = Mock()
        result_mock.rows = [("Asset", "Agent", "OK")]
        result_mock.syncro_assets = [{"name": "Asset"}]
        result_mock.huntress_agents = [{"hostname": "Agent"}]
        mock_service.fetch_and_compare.return_value = result_mock

        # Track signals
        signals = {"progress": [], "result": [], "raw_data": [], "finished": False, "error": []}
        
        worker.progress.connect(signals["progress"].append)
        worker.result.connect(signals["result"].append)
        worker.raw_data.connect(signals["raw_data"].append)
        worker.finished_work.connect(lambda: signals.update({"finished": True}))
        worker.error.connect(signals["error"].append)

        # Execute
        worker.run()

        # Verify
        assert len(signals["result"]) == 1
        # PySide6 signals might convert tuples to lists, so we check content recursively or cast
        # result was [("Asset", "Agent", "OK")]
        # signal might be [[ 'Asset', 'Agent', 'OK' ]]
        result_rows = signals["result"][0]
        assert len(result_rows) == 1
        # Check first row elements
        assert tuple(result_rows[0]) == ("Asset", "Agent", "OK")
        assert len(signals["raw_data"]) == 1
        assert signals["finished"] is True
        assert len(signals["error"]) == 0
        assert len(signals["progress"]) >= 2  # Initial + comparing + done

        # Verify calls
        mock_syncro_cls.assert_called_with(api_key="syncro_key", subdomain="syncro_sub")
        mock_huntress_cls.assert_called_with(api_key="huntress_key", secret_key="huntress_secret")
        mock_service.fetch_and_compare.assert_called_once()

    @patch("gui.workers.comparison_worker.SyncroClient")
    def test_run_error_emits_error_signal(self, mock_syncro_cls, worker):
        """Test that exception during run emits error signal."""
        mock_syncro_cls.side_effect = Exception("API Error")

        errors = []
        worker.error.connect(errors.append)
        worker.finished_work.connect(lambda: pytest.fail("Should not finish successfully"))

        worker.run()

        assert len(errors) == 1
        assert "API Error" in errors[0]

    @patch("gui.workers.comparison_worker.SyncroClient")
    @patch("gui.workers.comparison_worker.HuntressClient")
    @patch("gui.workers.comparison_worker.ComparisonService")
    def test_cancel_stops_execution(self, mock_service_cls, mock_huntress_cls, mock_syncro_cls, worker):
        """Test that cancellation stops execution."""
        # Cancel before run
        worker.cancel()
        
        results = []
        worker.result.connect(results.append)
        
        worker.run()
        
        # Should not have produced results
        assert len(results) == 0
        # Service might be init but fetch should be skipped or partially skipped depending on check placement
        # The code checks cancelled after client init and before fetch?
        # Let's check code: 
        #   Init clients...
        #   Init Service...
        #   Check cancelled
        #   Fetch...
        
        # If cancelled before run, it should check it.
        # But wait, logic is:
        #   ...
        #   service = ...
        #   if self._is_cancelled: return
        
        # So service IS instantiated.
        assert mock_service_cls.called
        # But fetch_and_compare should NOT be called?
        # Wait, code says:
        #   service = ComparisonService(...)
        #   if self._is_cancelled: return
        #   ...
        #   service.fetch_and_compare(...)
        
        mock_service_cls.return_value.fetch_and_compare.assert_not_called()
