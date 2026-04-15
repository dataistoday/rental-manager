"""sheets/tenants.py — Read/write helpers for the Tenants tab."""

import datetime
import pandas as pd

from sheets.client import get_all_records, append_row


COLUMNS = [
    "timestamp", "property", "tenant_name", "lease_start", "lease_end",
    "monthly_rent", "security_deposit", "entry_type", "entry_date",
    "subject", "body", "doc_url",
]


def get_tenants() -> pd.DataFrame:
    """Return all tenant log rows as a DataFrame."""
    df = get_all_records("tenants")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def get_tenants_for_property(property_name: str) -> pd.DataFrame:
    """Return tenant rows for a specific property, newest first."""
    df = get_tenants()
    if df.empty:
        return df
    filtered = df[df["property"] == property_name].copy()
    if "entry_date" in filtered.columns:
        filtered = filtered.sort_values("entry_date", ascending=False)
    return filtered


def add_tenant_log(
    property_name: str,
    tenant_name: str,
    entry_type: str,
    entry_date: datetime.date,
    subject: str,
    body: str,
    lease_start: str = "",
    lease_end: str = "",
    monthly_rent: float = 0.0,
    security_deposit: float = 0.0,
    doc_url: str = "",
) -> None:
    """Append a tenant log entry."""
    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        property_name, tenant_name,
        lease_start, lease_end,
        round(monthly_rent, 2) if monthly_rent else "",
        round(security_deposit, 2) if security_deposit else "",
        entry_type,
        entry_date.isoformat(),
        subject, body, doc_url,
    ]
    append_row("tenants", row)
