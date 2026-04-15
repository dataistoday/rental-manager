"""
sheets/client.py

Low-level Sheets access. All other sheets/*.py modules use get_worksheet()
rather than calling gspread directly. This centralises caching and error handling.
"""

import os
import streamlit as st
import gspread
import pandas as pd

from auth.google_auth import get_gspread_client
from config import SHEET_TABS, CACHE_TTL_SECONDS


def _spreadsheet_id() -> str:
    """Resolve spreadsheet ID from env or st.secrets."""
    sid = os.getenv("SPREADSHEET_ID") or st.secrets.get("SPREADSHEET_ID", "")
    if not sid or sid == "REPLACE_WITH_SPREADSHEET_ID":
        raise ValueError(
            "SPREADSHEET_ID is not configured. "
            "Set it in your .env file (local) or Streamlit secrets (cloud)."
        )
    return sid


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_all_records(tab_key: str) -> pd.DataFrame:
    """
    Fetch all rows from a sheet tab and return as a DataFrame.
    Results are cached for CACHE_TTL_SECONDS seconds.

    tab_key must be one of the keys in config.SHEET_TABS
    (e.g. "expenses", "mileage", etc.)
    """
    tab_name = SHEET_TABS[tab_key]
    client = get_gspread_client()
    ws = client.open_by_key(_spreadsheet_id()).worksheet(tab_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def get_worksheet(tab_key: str) -> gspread.Worksheet:
    """
    Return a live gspread Worksheet object (not cached — use for writes).
    tab_key must be one of the keys in config.SHEET_TABS.
    """
    tab_name = SHEET_TABS[tab_key]
    client = get_gspread_client()
    return client.open_by_key(_spreadsheet_id()).worksheet(tab_name)


def append_row(tab_key: str, row: list) -> None:
    """Append a single row to the given tab and bust the read cache."""
    ws = get_worksheet(tab_key)
    ws.append_row(row, value_input_option="USER_ENTERED")
    # Invalidate the cached read so the next fetch reflects the new row
    get_all_records.clear()


def update_row(tab_key: str, row_index: int, row: list) -> None:
    """
    Overwrite an existing row (1-indexed, where row 1 is the header).
    row_index=2 means the first data row.
    """
    ws = get_worksheet(tab_key)
    col_count = len(row)
    # Build A1 range e.g. "A3:M3"
    end_col = chr(ord("A") + col_count - 1)
    cell_range = f"A{row_index}:{end_col}{row_index}"
    ws.update(cell_range, [row], value_input_option="USER_ENTERED")
    get_all_records.clear()
