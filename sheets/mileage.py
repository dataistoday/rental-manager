"""sheets/mileage.py — Read/write helpers for the Mileage tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row
from config import IRS_MILEAGE_RATE_CURRENT


COLUMNS = [
    "timestamp", "date", "property", "purpose",
    "start_odometer", "end_odometer", "miles",
    "irs_rate", "deduction_amount", "notes", "vehicle",
]


def get_mileage() -> pd.DataFrame:
    """Return all mileage rows as a DataFrame."""
    df = get_all_records("mileage")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_mileage(
    date: datetime.date,
    property_name: str,
    purpose: str,
    start_odometer: float,
    end_odometer: float,
    notes: str = "",
    irs_rate: float = IRS_MILEAGE_RATE_CURRENT,
    vehicle: str = "",
) -> None:
    """Append one mileage row. Calculates miles and deduction automatically."""
    miles = round(end_odometer - start_odometer, 1)
    deduction = round(miles * irs_rate, 2)
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        date.isoformat(),
        property_name,
        purpose,
        round(start_odometer, 1),
        round(end_odometer, 1),
        miles,
        irs_rate,
        deduction,
        notes,
        vehicle,
    ]
    append_row("mileage", row)
