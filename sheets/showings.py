"""sheets/showings.py — Read/write helpers for the Showings tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "property", "name", "location_found",
    "date", "time", "notes",
]


def get_showings() -> pd.DataFrame:
    df = get_all_records("showings")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_showing(
    property: str,
    name: str,
    location_found: str = "",
    date: str = "",
    time: str = "",
    notes: str = "",
) -> None:
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        property, name, location_found, date, time, notes,
    ]
    append_row("showings", row)
