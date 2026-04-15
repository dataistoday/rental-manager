"""sheets/expenses.py — Read/write helpers for the Expenses tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "property", "date", "vendor", "amount",
    "category", "description", "receipt_url", "payment_method", "notes",
]


def get_expenses() -> pd.DataFrame:
    """Return all expense rows as a DataFrame."""
    df = get_all_records("expenses")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_expense(
    property_name: str,
    date: datetime.date,
    vendor: str,
    amount: float,
    category: str,
    description: str = "",
    receipt_url: str = "",
    payment_method: str = "",
    notes: str = "",
) -> None:
    """Append one expense row to the Expenses sheet."""
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        property_name,
        date.isoformat(),
        vendor,
        round(amount, 2),
        category,
        description,
        receipt_url,
        payment_method,
        notes,
    ]
    append_row("expenses", row)
