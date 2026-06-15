from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from const import (
    MAX_NAME_WIDTH,
    STATUS_MISSING_HUNTRESS,
    STATUS_MISSING_SYNCRO,
    STATUS_OK,
)

if TYPE_CHECKING:
    from api.client import HuntressClient, SyncroClient


@dataclass
class ComparisonRow:
    """A single comparison result row."""

    syncro_name: str
    huntress_name: str
    status: str
    organization: str = ""


@dataclass
class ComparisonResult:
    """Dataclass to hold comparison results."""

    syncro_assets: List[Dict]
    huntress_agents: List[Dict]
    rows: List[ComparisonRow]
    syncro_count: int
    huntress_count: int


def normalize(name: str, length: int = MAX_NAME_WIDTH) -> Optional[str]:
    """Normalize asset name for comparison.

    Truncates to ``length`` (15 by default) because Syncro stores the
    NetBIOS-capped computer name while Huntress stores the full hostname.
    See ``const.MAX_NAME_WIDTH``.
    """
    if not name:
        return None
    return name.strip().lower()[:length]


def row_key(row: "ComparisonRow") -> str:
    """Stable ignore/identity key for a row (normalized comparison hostname)."""
    return normalize(row.syncro_name) or normalize(row.huntress_name) or ""


def extract_org(asset: Dict) -> str:
    """Extract the organization (Syncro customer) name from an asset."""
    customer = asset.get("customer")
    if isinstance(customer, dict):
        for key in ("business_name", "business_and_full_name", "fullname"):
            value = customer.get(key)
            if value and str(value).strip():
                return str(value).strip()
    value = asset.get("customer_business_then_name")
    if value and str(value).strip():
        return str(value).strip()
    return ""


class ComparisonService:
    """Service for comparing Syncro assets and Huntress agents."""

    def __init__(
        self, syncro_client: "SyncroClient", huntress_client: "HuntressClient"
    ):
        self.syncro_client = syncro_client
        self.huntress_client = huntress_client

    def fetch_and_compare(self, mismatches_first: bool = True) -> ComparisonResult:
        """Fetch data from both APIs and perform comparison."""
        from concurrent.futures import ThreadPoolExecutor

        # Fetch data in parallel
        # Note: We let the caller handle the spinner/progress indication
        with ThreadPoolExecutor(max_workers=3) as executor:
            huntress_future = executor.submit(self.huntress_client.get_all_agents)
            syncro_future = executor.submit(self.syncro_client.get_all_assets)
            org_future = executor.submit(self._fetch_huntress_org_names)

            huntress_agents = huntress_future.result()
            syncro_assets = syncro_future.result()
            org_id_to_name = org_future.result()

        rows = self._build_comparison(
            syncro_assets,
            huntress_agents,
            org_id_to_name,
            mismatches_first=mismatches_first,
        )

        # Calculate asset counts (unique normalized)
        syncro_count = len(self._build_map(syncro_assets))
        huntress_count = len(self._build_map(huntress_agents, key_field="hostname"))

        return ComparisonResult(
            syncro_assets=syncro_assets,
            huntress_agents=huntress_agents,
            rows=rows,
            syncro_count=syncro_count,
            huntress_count=huntress_count,
        )

    def _build_map(
        self, items: List[Dict], key_field: str = "name"
    ) -> Dict[str, Set[str]]:
        """Build a map of normalized names to original names."""
        item_map = {}
        for item in items:
            raw = item.get(key_field) or ""
            normalized = normalize(raw)
            if normalized:
                item_map.setdefault(normalized, set()).add(raw.strip())
        return item_map

    def _build_org_map(self, syncro_assets: List[Dict]) -> Dict[str, str]:
        """Build a map of normalized Syncro name -> organization name."""
        org_map: Dict[str, str] = {}
        for asset in syncro_assets:
            normalized = normalize(asset.get("name") or "")
            if not normalized:
                continue
            # Keep the first non-empty organization seen for this key.
            if org_map.get(normalized):
                continue
            org = extract_org(asset)
            if org:
                org_map[normalized] = org
        return org_map

    def _fetch_huntress_org_names(self) -> Dict[int, str]:
        """Fetch Huntress organization id -> name. Degrades to {} on failure."""
        try:
            orgs = self.huntress_client.get_all_organizations()
            return {
                o["id"]: o.get("name", "")
                for o in orgs
                if isinstance(o, dict) and o.get("id") is not None
            }
        except Exception:
            # Org names are a nice-to-have; never fail the whole comparison.
            return {}

    def _build_huntress_org_map(
        self, huntress_agents: List[Dict], org_id_to_name: Dict[int, str]
    ) -> Dict[str, str]:
        """Build a map of normalized Huntress hostname -> organization name."""
        org_map: Dict[str, str] = {}
        if not org_id_to_name:
            return org_map
        for agent in huntress_agents:
            normalized = normalize(agent.get("hostname") or "")
            if not normalized or org_map.get(normalized):
                continue
            name = org_id_to_name.get(agent.get("organization_id"))
            if name:
                org_map[normalized] = name
        return org_map

    def _build_comparison(
        self,
        syncro_assets: List[Dict],
        huntress_agents: List[Dict],
        org_id_to_name: Optional[Dict[int, str]] = None,
        mismatches_first: bool = True,
    ) -> List[ComparisonRow]:
        """Build comparison rows from data."""
        syncro_map = self._build_map(syncro_assets, "name")
        huntress_map = self._build_map(huntress_agents, "hostname")
        org_map = self._build_org_map(syncro_assets)
        huntress_org_map = self._build_huntress_org_map(
            huntress_agents, org_id_to_name or {}
        )

        all_keys = sorted(set(syncro_map.keys()) | set(huntress_map.keys()))
        rows: List[ComparisonRow] = []

        for key in all_keys:
            s_names = syncro_map.get(key)
            h_names = huntress_map.get(key)

            s_display = "; ".join(sorted(s_names)) if s_names else ""
            h_display = "; ".join(sorted(h_names)) if h_names else ""

            if s_names and h_names:
                status = STATUS_OK
            elif s_names and not h_names:
                status = STATUS_MISSING_HUNTRESS
            else:
                status = STATUS_MISSING_SYNCRO

            organization = org_map.get(key) or huntress_org_map.get(key, "")

            rows.append(
                ComparisonRow(
                    syncro_name=s_display,
                    huntress_name=h_display,
                    status=status,
                    organization=organization,
                )
            )

        # Sort based on configuration
        if mismatches_first:
            # Errors/Mismatches first, OK at bottom
            rows.sort(
                key=lambda r: (
                    0 if r.status != STATUS_OK else 1,
                    r.syncro_name.lower(),
                    r.huntress_name.lower(),
                )
            )
        else:
            # OK first, Errors/Mismatches at bottom
            rows.sort(
                key=lambda r: (
                    0 if r.status == STATUS_OK else 1,
                    r.syncro_name.lower(),
                    r.huntress_name.lower(),
                )
            )

        return rows
