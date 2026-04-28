"""sheets/rent_income.py — Read/write helpers for the Rent Income tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "property", "tenant_name", "date_received", "amount",
    "late_fee", "period_start", "period_end", "payment_method", "notes",
]


def get_rent_income() -> pd.DataFrame:
    df = get_all_records("rent_income")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def add_rent_payment(
    property: str,
    tenant_name: str,
    date_received: str,
    amount: float,
    late_fee: float = 0.0,
    period_start: str = "",
    period_end: str = "",
    payment_method: str = "",
    notes: str = "",
) -> None:
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        property, tenant_name, date_received,
        round(amount, 2),
        round(late_fee, 2) if late_fee else "",
        period_start, period_end, payment_method, notes,
    ]
    append_row("rent_income", row)
