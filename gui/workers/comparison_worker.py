"""Worker thread for running comparison operations."""

import random
from typing import Dict

from PySide6.QtCore import QThread, Signal

from api.client import HuntressClient, SyncroClient
from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
from services.comparison import ComparisonRow, ComparisonService

_FAKE_ORGS = [
    "Acme Corp",
    "Globex Industries",
    "Initech LLC",
    "Umbrella Services",
    "Wayne Enterprises",
    "Stark Solutions",
    "Oscorp Technologies",
    "Cyberdyne Systems",
]

_FAKE_HOSTS = [
    "DC-SERVER01",
    "WS-RECEPTION",
    "WS-ACCOUNTING",
    "LAPTOP-SALES03",
    "SERVER-BACKUP",
    "WS-EXEC-01",
    "LAPTOP-HR-02",
    "DC-SECONDARY",
    "WS-WAREHOUSE",
    "SERVER-FILES",
    "LAPTOP-IT-05",
    "WS-DESIGN-02",
    "SERVER-SQL",
    "WS-FRONTDESK",
    "LAPTOP-MGR-01",
    "NAS-ARCHIVE",
    "WS-DEV-03",
    "SERVER-WEB",
    "LAPTOP-FIELD-04",
    "WS-CONFROOM",
]


def _generate_fake_rows() -> list:
    """Generate a realistic set of comparison rows for GUI testing."""
    rows = []
    statuses = [STATUS_OK, STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO]
    weights = [0.6, 0.25, 0.15]

    for host in _FAKE_HOSTS:
        status = random.choices(statuses, weights=weights, k=1)[0]
        org = random.choice(_FAKE_ORGS)

        if status == STATUS_OK:
            syncro_name = host
            huntress_name = host
        elif status == STATUS_MISSING_HUNTRESS:
            syncro_name = host
            huntress_name = ""
        else:
            syncro_name = ""
            huntress_name = host

        rows.append(
            ComparisonRow(
                syncro_name=syncro_name,
                huntress_name=huntress_name,
                status=status,
                organization=org,
            )
        )

    rows.sort(key=lambda r: (0 if r.status != STATUS_OK else 1, r.syncro_name or r.huntress_name))
    return rows


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
            if self.settings.get("UseFakeData"):
                self.progress.emit("Generating fake data...")
                rows = _generate_fake_rows()
                self.raw_data.emit({"syncro": [], "huntress": []})
                self.result.emit(rows)
                self.progress.emit("Fake comparison complete")
                self.finished_work.emit()
                return

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
            # the ThreadPoolExecutor. For now, we wait for the service
            # to return the full result.
            comparison_result = service.fetch_and_compare(mismatches_first=True)

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
