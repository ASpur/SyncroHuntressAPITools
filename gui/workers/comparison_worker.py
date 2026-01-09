"""Worker thread for running comparison operations."""

from typing import Dict, List, Tuple, Optional

from PySide6.QtCore import QThread, Signal

from api import huntress, syncro
from services.comparison import normalize


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
            # Fetch Huntress agents
            self.progress.emit("Fetching Huntress agents...")
            if self._is_cancelled:
                return

            huntress_agents = huntress.get_agents(self.settings)

            if self._is_cancelled:
                return

            # Fetch Syncro assets
            self.progress.emit("Fetching Syncro assets...")
            syncro_assets = syncro.get_all_assets(self.settings)

            if self._is_cancelled:
                return

            # Emit raw data for debug view
            self.raw_data.emit({
                "syncro": syncro_assets,
                "huntress": huntress_agents,
            })

            # Build comparison
            self.progress.emit("Comparing agents...")
            rows = self._build_comparison(syncro_assets, huntress_agents)

            if self._is_cancelled:
                return

            self.result.emit(rows)
            self.progress.emit("Comparison complete")
            self.finished_work.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _build_comparison(
        self, syncro_assets: List[Dict], huntress_agents: List[Dict]
    ) -> List[Tuple[str, str, str]]:
        """Build comparison rows from API data."""
        # Build maps from normalized -> set(original names)
        syncro_map = {}
        for asset in syncro_assets:
            raw = asset.get("name") or ""
            normalized = normalize(raw)
            if normalized:
                syncro_map.setdefault(normalized, set()).add(raw.strip())

        huntress_map = {}
        for agent in huntress_agents:
            raw = agent.get("hostname") or ""
            normalized = normalize(raw)
            if normalized:
                huntress_map.setdefault(normalized, set()).add(raw.strip())

        # Build comparison rows
        all_keys = sorted(set(syncro_map.keys()) | set(huntress_map.keys()))
        rows = []

        for key in all_keys:
            s_names = syncro_map.get(key)
            h_names = huntress_map.get(key)

            s_display = "; ".join(sorted(s_names)) if s_names else ""
            h_display = "; ".join(sorted(h_names)) if h_names else ""

            if s_names and h_names:
                status = "OK!"
            elif s_names and not h_names:
                status = "Missing in Huntress"
            else:
                status = "Missing in Syncro"

            rows.append((s_display, h_display, status))

        # Sort: Missing first, OK at bottom, then alphabetical
        rows.sort(key=lambda r: (0 if r[2] != "OK!" else 1, r[0].lower(), r[1].lower()))

        return rows
