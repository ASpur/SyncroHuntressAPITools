"""Worker thread for running comparison operations."""

from typing import Dict

from PySide6.QtCore import QThread, Signal

from api.client import HuntressClient, SyncroClient
from services.comparison import ComparisonService


class ComparisonWorker(QThread):
    """Worker thread for fetching API data and running comparisons."""

    progress = Signal(str)
    error = Signal(str)
    result = Signal(list)  # List of (syncro, huntress, status) tuples
    raw_data = Signal(dict)  # {"syncro": [...], "huntress": [...]}
    finished_work = Signal()

    def __init__(self, settings: Dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of the operation."""
        self._is_cancelled = True

    def run(self):
        """Execute the comparison operation."""
        try:
            self.progress.emit("Initializing clients...")

            syncro_client = SyncroClient(
                api_key=self.settings["SyncroAPIKey"],
                subdomain=self.settings["SyncroSubDomain"],
            )
            huntress_client = HuntressClient(
                api_key=self.settings["HuntressAPIKey"],
                secret_key=self.settings["HuntressSecretKey"],
            )

            service = ComparisonService(syncro_client, huntress_client)

            if self._is_cancelled:
                return

            self.progress.emit("Fetching and comparing data...")
            # Note: In a real GUI, we might want granular progress from
            # the ThreadPoolExecutor. For now, we wait for the service
            # to return the full result.
            comparison_result = service.fetch_and_compare()

            if self._is_cancelled:
                return

            # Emit raw data for debug view
            self.raw_data.emit(
                {
                    "syncro": comparison_result.syncro_assets,
                    "huntress": comparison_result.huntress_agents,
                }
            )

            if self._is_cancelled:
                return

            self.result.emit(comparison_result.rows)
            self.progress.emit("Comparison complete")
            self.finished_work.emit()

        except Exception as e:
            self.error.emit(str(e))
