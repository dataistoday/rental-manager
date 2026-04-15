"""sheets/inspections.py — Read/write helpers for the Inspections tab."""

import uuid
import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "id", "timestamp", "property", "inspection_type", "inspection_date",
    "inspector", "condition_overall", "notes", "action_items", "photo_urls",
]


def get_inspections() -> pd.DataFrame:
    """Return all inspection rows as a DataFrame."""
    df = get_all_records("inspections")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_inspection(
    property_name: str,
    inspection_type: str,
    inspection_date: datetime.date,
    inspector: str = "",
    condition_overall: str = "",
    notes: str = "",
    action_items: str = "",
    photo_urls: str = "",
) -> str:
    """Append a new inspection record. Returns the generated ID."""
    inspection_id = str(uuid.uuid4())[:8].upper()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    row = [
        inspection_id, now, property_name, inspection_type,
        inspection_date.isoformat(), inspector, condition_overall,
        notes, action_items, photo_urls,
    ]
    append_row("inspections", row)
    return inspection_id
