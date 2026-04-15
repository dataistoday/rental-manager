"""sheets/vendors.py — Read/write helpers for the Vendors tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "company_name", "contact_name", "phone", "email",
    "trade", "properties_served", "hourly_rate", "rating", "notes", "last_used_date",
]


def get_vendors() -> pd.DataFrame:
    """Return all vendor rows as a DataFrame."""
    df = get_all_records("vendors")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_vendor(
    company_name: str,
    contact_name: str = "",
    phone: str = "",
    email: str = "",
    trade: str = "",
    properties_served: str = "All",
    hourly_rate: float = 0.0,
    rating: int = 0,
    notes: str = "",
    last_used_date: str = "",
) -> None:
    """Append a new vendor row."""
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        company_name, contact_name, phone, email,
        trade, properties_served,
        round(hourly_rate, 2) if hourly_rate else "",
        rating if rating else "",
        notes, last_used_date,
    ]
    append_row("vendors", row)
