"""sheets/maintenance.py — Read/write/update helpers for the Maintenance tab."""

import uuid
import datetime
import pandas as pd

from sheets.client import get_all_records, append_row, update_row, get_worksheet


COLUMNS = [
    "id", "timestamp", "last_updated", "property", "issue_title",
    "description", "status", "priority", "contractor",
    "estimated_cost", "actual_cost", "photo_urls", "resolution_notes",
]


def get_maintenance() -> pd.DataFrame:
    """Return all maintenance rows as a DataFrame."""
    df = get_all_records("maintenance")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_maintenance(
    property_name: str,
    issue_title: str,
    description: str = "",
    status: str = "Open",
    priority: str = "Medium",
    contractor: str = "",
    estimated_cost: float = 0.0,
    photo_urls: str = "",
) -> str:
    """Append a new maintenance issue. Returns the generated UUID."""
    issue_id = str(uuid.uuid4())[:8].upper()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    row = [
        issue_id, now, now, property_name, issue_title,
        description, status, priority, contractor,
        round(estimated_cost, 2), "", photo_urls, "",
    ]
    append_row("maintenance", row)
    return issue_id


def update_maintenance_status(
    row_index: int,
    existing_row: list,
    status: str,
    actual_cost: float = None,
    resolution_notes: str = "",
) -> None:
    """
    Update status (and optionally cost + notes) on an existing maintenance row.
    row_index is 1-based sheet row number (2 = first data row).
    existing_row is the full list of values for that row.
    """
    updated = list(existing_row)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    # Column indices (0-based within the row list)
    updated[2] = now                # last_updated
    updated[6] = status             # status
    if actual_cost is not None:
        updated[10] = round(actual_cost, 2)
    if resolution_notes:
        updated[12] = resolution_notes
    update_row("maintenance", row_index, updated)
