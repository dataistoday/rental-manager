"""sheets/vehicle_snapshots.py — Read/write helpers for the Vehicle Snapshots tab.

One row per (tax_year, vehicle). Captures the year-start and year-end odometer
readings needed for Form 4562 Part V (Listed Property).
"""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "tax_year", "vehicle",
    "jan_1_odometer", "dec_31_odometer",
    "placed_in_service_date", "has_other_personal_vehicle",
    "notes",
]


def get_vehicle_snapshots() -> pd.DataFrame:
    df = get_all_records("vehicle_snapshots")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_vehicle_snapshot(
    tax_year: int,
    vehicle: str,
    jan_1_odometer: float = 0.0,
    dec_31_odometer: float = 0.0,
    placed_in_service_date: str = "",
    has_other_personal_vehicle: str = "",
    notes: str = "",
) -> None:
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        tax_year, vehicle,
        int(jan_1_odometer) if jan_1_odometer else "",
        int(dec_31_odometer) if dec_31_odometer else "",
        placed_in_service_date,
        has_other_personal_vehicle,
        notes,
    ]
    append_row("vehicle_snapshots", row)
