import os
import json
from typing import Dict, List, Tuple, Optional
from api import syncro, huntress
from utils.output import write_csv, write_ascii_table, print_colored_table, Spinner

MAX_NAME_WIDTH = 15
def normalize(name: str, length: int = MAX_NAME_WIDTH) -> Optional[str]:
    """Normalize asset name for comparison"""
    if not name:
        return None
    return name.strip().lower()[:length]

def compare_agents(
    settings: Dict,
    output_file: Optional[str] = None,
    use_color: bool = True,
    output_format: str = "csv"
) -> None:
    """Compare Syncro and Huntress agents"""
    from concurrent.futures import ThreadPoolExecutor

    # Fetch data from both APIs in parallel
    with Spinner("Fetching agents from APIs"):
        with ThreadPoolExecutor(max_workers=2) as executor:
            huntress_future = executor.submit(huntress.get_agents, settings)
            syncro_future = executor.submit(syncro.get_all_assets, settings)
            huntress_agents = huntress_future.result()
            syncro_assets = syncro_future.result()

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

    # Debug dumps
    if settings.get("debug"):
        os.makedirs("debug", exist_ok=True)
        with open("debug/agentDumpSyncro.json", "w") as f:
            json.dump(syncro_assets, f, indent=4)
        with open("debug/agentDumpHuntress.json", "w") as f:
            json.dump(huntress_agents, f, indent=4)

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

    # Sort: OK first, errors at bottom, then alphabetical
    rows.sort(key=lambda r: (0 if r[2] == "OK!" else 1, r[0].lower(), r[1].lower()))

    # Write to file if requested
    if output_file:
        try:
            if output_format == "csv":
                write_csv(output_file, rows)
            elif output_format == "ascii":
                write_ascii_table(output_file, rows)
            print(f"Results written to {output_file}")
        except Exception as e:
            print(f"Failed to write {output_format.upper()} {output_file}: {e}")

    # Print to console
    print_colored_table(rows, use_color)