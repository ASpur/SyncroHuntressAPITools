from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
from api.client import SyncroClient, HuntressClient
from const import MAX_NAME_WIDTH

@dataclass
class ComparisonResult:
    """Dataclass to hold comparison results."""
    syncro_assets: List[Dict]
    huntress_agents: List[Dict]
    rows: List[Tuple[str, str, str]]
    syncro_count: int
    huntress_count: int

def normalize(name: str, length: int = MAX_NAME_WIDTH) -> Optional[str]:
    """Normalize asset name for comparison."""
    if not name:
        return None
    return name.strip().lower()[:length]

class ComparisonService:
    """Service for comparing Syncro assets and Huntress agents."""

    def __init__(self, syncro_client: SyncroClient, huntress_client: HuntressClient):
        self.syncro_client = syncro_client
        self.huntress_client = huntress_client

    def fetch_and_compare(self) -> ComparisonResult:
        """Fetch data from both APIs and perform comparison."""
        from concurrent.futures import ThreadPoolExecutor

        # Fetch data in parallel
        # Note: We let the caller handle the spinner/progress indication
        with ThreadPoolExecutor(max_workers=2) as executor:
            huntress_future = executor.submit(self.huntress_client.get_agents)
            syncro_future = executor.submit(self.syncro_client.get_all_assets)
            
            huntress_agents = huntress_future.result()
            syncro_assets = syncro_future.result()

        rows = self._build_comparison(syncro_assets, huntress_agents)
        
        # Calculate asset counts (unique normalized)
        syncro_count = len(self._build_map(syncro_assets))
        huntress_count = len(self._build_map(huntress_agents, key_field="hostname"))

        return ComparisonResult(
            syncro_assets=syncro_assets,
            huntress_agents=huntress_agents,
            rows=rows,
            syncro_count=syncro_count,
            huntress_count=huntress_count
        )

    def _build_map(self, items: List[Dict], key_field: str = "name") -> Dict[str, Set[str]]:
        """Build a map of normalized names to original names."""
        item_map = {}
        for item in items:
            raw = item.get(key_field) or ""
            normalized = normalize(raw)
            if normalized:
                item_map.setdefault(normalized, set()).add(raw.strip())
        return item_map

    def _build_comparison(
        self, syncro_assets: List[Dict], huntress_agents: List[Dict]
    ) -> List[Tuple[str, str, str]]:
        """Build comparison rows from data."""
        syncro_map = self._build_map(syncro_assets, "name")
        huntress_map = self._build_map(huntress_agents, "hostname")

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

        # Sort: OK first, errors at bottom, then alphabetical
        # Note: Previous sort was OK first. User might prefer problems first?
        # Keeping existing logic: OK at top.
        rows.sort(key=lambda r: (0 if r[2] == "OK!" else 1, r[0].lower(), r[1].lower()))
        
        return rows