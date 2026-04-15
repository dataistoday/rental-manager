"""sheets/utilities.py — Read/write helpers for the Utilities tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "property", "utility_type", "provider", "account_number",
    "billing_period", "amount", "due_date", "paid_date", "notes",
]


def get_utilities() -> pd.DataFrame:
    """Return all utility rows as a DataFrame."""
    df = get_all_records("utilities")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_utility(
    property_name: str,
    utility_type: str,
    provider: str,
    amount: float,
    billing_period: str = "",
    account_number: str = "",
    due_date: datetime.date | None = None,
    paid_date: datetime.date | None = None,
    notes: str = "",
) -> None:
    """Append a utility bill record."""
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        property_name,
        utility_type,
        provider,
        account_number,
        billing_period,
        round(amount, 2),
        due_date.isoformat() if due_date else "",
        paid_date.isoformat() if paid_date else "",
        notes,
    ]
    append_row("utilities", row)
