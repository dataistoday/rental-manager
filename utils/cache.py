"""
utils/cache.py

Graceful-degradation wrappers around every Sheets read.

Pattern: try the live fetch → on failure, return last-known cached DataFrame
plus an error string. The page then shows st.warning rather than crashing.

Usage:
    df, err = safe_get_expenses()
    if err:
        st.warning(f"Using cached data — Sheets unreachable. ({err})")
    if df is not None:
        st.dataframe(df)
"""

import pandas as pd
import streamlit as st

import sheets.expenses as _exp
import sheets.mileage as _mil
import sheets.maintenance as _mnt
import sheets.insurance as _ins
import sheets.vendors as _ven
import sheets.tenants as _ten
import sheets.inspections as _insp

# Module-level cache survives across Streamlit reruns within the same session
_last_known: dict[str, pd.DataFrame] = {}


def _safe_fetch(key: str, fetch_fn) -> tuple[pd.DataFrame | None, str | None]:
    try:
        df = fetch_fn()
        _last_known[key] = df
        return df, None
    except Exception as e:
        cached = _last_known.get(key)
        return cached, str(e)


def safe_get_expenses():
    return _safe_fetch("expenses", _exp.get_expenses)


def safe_get_mileage():
    return _safe_fetch("mileage", _mil.get_mileage)


def safe_get_maintenance():
    return _safe_fetch("maintenance", _mnt.get_maintenance)


def safe_get_insurance():
    return _safe_fetch("insurance", _ins.get_insurance)


def safe_get_vendors():
    return _safe_fetch("vendors", _ven.get_vendors)


def safe_get_tenants():
    return _safe_fetch("tenants", _ten.get_tenants)


def safe_get_inspections():
    return _safe_fetch("inspections", _insp.get_inspections)


def show_fetch_error(err: str | None) -> None:
    """Display a standardised warning banner if there was a fetch error."""
    if err:
        st.warning(
            f"Google Sheets is unreachable — showing last known data.  \n`{err}`",
            icon="⚠️",
        )
