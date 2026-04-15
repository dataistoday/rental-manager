"""
pages/10_utility_tracker.py — Utility Tracker

Log utility bills per property (electric, water, gas, HOA, etc.).
Tracks provider, billing period, amount, due date, and paid date.
"""

import datetime
import pandas as pd
import streamlit as st

from sheets.utilities import add_utility
from utils.cache import safe_get_utilities, show_fetch_error
from utils.formatting import format_currency, format_date
from config import PROPERTIES, UTILITY_TYPES

st.set_page_config(page_title="Utility Tracker", page_icon="⚡", layout="centered")
st.title("⚡ Utility Tracker")
st.caption("Log and track utility bills by property.")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df, err = safe_get_utilities()
show_fetch_error(err)

# ---------------------------------------------------------------------------
# Filters + summary
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    prop_filter = st.selectbox("Property", ["All"] + PROPERTIES, key="util_prop")
with col2:
    type_filter = st.selectbox("Utility", ["All"] + UTILITY_TYPES, key="util_type")

filtered = df.copy() if df is not None and not df.empty else pd.DataFrame()

if not filtered.empty:
    filtered["amount"] = pd.to_numeric(filtered["amount"], errors="coerce").fillna(0)
    if prop_filter != "All":
        filtered = filtered[filtered["property"] == prop_filter]
    if type_filter != "All":
        filtered = filtered[filtered["utility_type"] == type_filter]
    filtered = filtered.sort_values("timestamp", ascending=False, na_position="last")

# Summary metrics
if not filtered.empty:
    total = filtered["amount"].sum()
    current_year = datetime.date.today().year
    ytd_mask = filtered["timestamp"].astype(str).str[:4] == str(current_year)
    ytd_total = filtered.loc[ytd_mask, "amount"].sum() if ytd_mask.any() else 0.0

    col1, col2 = st.columns(2)
    col1.metric("Total (filtered)", format_currency(total))
    col2.metric(f"{current_year} YTD", format_currency(ytd_total))

st.markdown("---")

# ---------------------------------------------------------------------------
# Bill history table
# ---------------------------------------------------------------------------
st.subheader("Bill History")

if filtered.empty:
    st.info("No utility bills logged yet. Add one below.", icon="ℹ️")
else:
    display_cols = ["property", "utility_type", "provider", "billing_period", "amount", "due_date", "paid_date"]
    available = [c for c in display_cols if c in filtered.columns]
    display_df = filtered[available].copy()

    if "amount" in display_df.columns:
        display_df["amount"] = display_df["amount"].apply(
            lambda x: format_currency(x) if pd.notna(x) else ""
        )
    if "due_date" in display_df.columns:
        display_df["due_date"] = display_df["due_date"].apply(format_date)
    if "paid_date" in display_df.columns:
        display_df["paid_date"] = display_df["paid_date"].apply(
            lambda x: format_date(x) if x else "Unpaid"
        )

    display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Unpaid bills callout
    if "paid_date" in filtered.columns:
        unpaid = filtered[filtered["paid_date"].astype(str).str.strip() == ""]
        if not unpaid.empty:
            st.warning(
                f"{len(unpaid)} unpaid bill(s) in current view — check Paid Date column.",
                icon="⚠️",
            )

# ---------------------------------------------------------------------------
# Log new bill
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Log Utility Bill")

with st.form("utility_form", clear_on_submit=True):
    prop = st.selectbox("Property *", PROPERTIES)

    col1, col2 = st.columns(2)
    with col1:
        util_type = st.selectbox("Utility Type *", UTILITY_TYPES)
    with col2:
        provider = st.text_input("Provider", placeholder="Duke Energy, TECO…")

    col3, col4 = st.columns(2)
    with col3:
        amount = st.number_input("Amount ($) *", min_value=0.0, step=1.0, format="%.2f")
    with col4:
        billing_period = st.text_input("Billing Period", placeholder="Jan 2025, Q1 2025…")

    col5, col6 = st.columns(2)
    with col5:
        due_date = st.date_input("Due Date", value=None)
    with col6:
        paid_date = st.date_input("Paid Date (leave blank if unpaid)", value=None)

    account_number = st.text_input("Account Number (optional)")
    notes = st.text_input("Notes (optional)")

    submitted = st.form_submit_button("Save Bill", use_container_width=True)
    if submitted:
        if amount <= 0:
            st.error("Amount must be greater than $0.")
        else:
            try:
                add_utility(
                    property_name=prop,
                    utility_type=util_type,
                    provider=provider.strip(),
                    amount=amount,
                    billing_period=billing_period.strip(),
                    account_number=account_number.strip(),
                    due_date=due_date,
                    paid_date=paid_date,
                    notes=notes.strip(),
                )
                st.success(f"Saved! {format_currency(amount)} · {util_type} · {prop}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
