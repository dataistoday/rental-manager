"""sheets/insurance.py — Read-only helpers for the Insurance tab."""

import pandas as pd
from sheets.client import get_all_records


COLUMNS = [
    "property", "policy_number", "insurer", "agent_name", "agent_phone",
    "agent_email", "premium_annual", "renewal_date", "coverage_type",
    "doc_url", "notes",
]


def get_insurance() -> pd.DataFrame:
    """Return all insurance records as a DataFrame."""
    df = get_all_records("insurance")
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df


def get_insurance_for_property(property_name: str) -> pd.DataFrame:
    """Return insurance records for a specific property."""
    df = get_insurance()
    if df.empty:
        return df
    return df[df["property"] == property_name]
