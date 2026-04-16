"""
pages/02_mileage_tracker.py — Mileage Tracker

Log start/end odometer readings. Miles and the IRS deduction are calculated
automatically. All trips are stored in the Mileage tab for Schedule E / tax prep.
"""

import datetime
import streamlit as st
import pandas as pd

from sheets.mileage import add_mileage
from utils.cache import safe_get_mileage, show_fetch_error
from utils.formatting import format_currency, format_miles, format_date
from config import PROPERTIES, MILEAGE_PURPOSES, VEHICLES, IRS_MILEAGE_RATE_CURRENT

st.set_page_config(page_title="Mileage Tracker", page_icon="🚗", layout="centered")
st.title("🚗 Mileage Tracker")
st.caption(f"IRS rate: ${IRS_MILEAGE_RATE_CURRENT}/mile (2026)")

# ---------------------------------------------------------------------------
# Log Trip form
# ---------------------------------------------------------------------------
st.subheader("Log a Trip")

with st.form("mileage_form", clear_on_submit=True):
    prop = st.selectbox(
        "Property (destination) *",
        PROPERTIES,
        index=PROPERTIES.index("Tampa"),
    )
    vehicle = st.selectbox("Vehicle *", VEHICLES)
    purpose = st.selectbox("Purpose *", MILEAGE_PURPOSES)
    trip_date = st.date_input("Date", value=datetime.date.today())

    col1, col2 = st.columns(2)
    with col1:
        start_odo = st.number_input(
            "Start Odometer (miles)", min_value=0.0, step=0.1, format="%.1f"
        )
    with col2:
        end_odo = st.number_input(
            "End Odometer (miles)", min_value=0.0, step=0.1, format="%.1f"
        )

    # Live preview
    if end_odo > start_odo:
        miles = round(end_odo - start_odo, 1)
        deduction = round(miles * IRS_MILEAGE_RATE_CURRENT, 2)
        st.info(f"**{miles} miles** → **{format_currency(deduction)} deduction**")

    notes = st.text_input("Notes (optional)", placeholder="e.g. Picked up supplies at Home Depot")

    submitted = st.form_submit_button("Save Trip", use_container_width=True)
    if submitted:
        errors = []
        if end_odo <= start_odo:
            errors.append("End odometer must be greater than start odometer.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                add_mileage(
                    date=trip_date,
                    property_name=prop,
                    purpose=purpose,
                    start_odometer=start_odo,
                    end_odometer=end_odo,
                    notes=notes.strip(),
                    vehicle=vehicle,
                )
                st.success(
                    f"Trip saved! {round(end_odo - start_odo, 1)} miles → "
                    f"{format_currency(round((end_odo - start_odo) * IRS_MILEAGE_RATE_CURRENT, 2))} deduction"
                )
            except Exception as e:
                st.error(f"Failed to save: {e}")

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
st.markdown("---")
col_title, col_refresh = st.columns([4, 1])
col_title.subheader("Trip History")
if col_refresh.button("Refresh", use_container_width=True):
    from sheets.client import get_all_records
    get_all_records.clear()
    st.rerun()

df, err = safe_get_mileage()
show_fetch_error(err)

if df is None or df.empty:
    st.info("No trips logged yet.", icon="ℹ️")
    st.stop()

# Filter by property
prop_filter = st.selectbox("Filter by property", ["All"] + PROPERTIES, key="ml_prop")
if prop_filter != "All":
    df = df[df["property"] == prop_filter]

if df.empty:
    st.info(f"No trips for {prop_filter}.")
    st.stop()

# Summary totals
total_miles = pd.to_numeric(df["miles"], errors="coerce").sum()
total_deduction = pd.to_numeric(df["deduction_amount"], errors="coerce").sum()

c1, c2 = st.columns(2)
c1.metric("Total Miles", f"{total_miles:,.1f}")
c2.metric("Total Deduction", format_currency(total_deduction))

# Display table — vehicle column is optional (may not exist in older rows)
wanted = ["date", "property", "vehicle", "purpose", "miles", "deduction_amount", "notes"]
present = [c for c in wanted if c in df.columns]
display_df = df[present].copy()
display_df.columns = [c.replace("_", " ").title() for c in present]
if "Deduction Amount" in display_df.columns:
    display_df.rename(columns={"Deduction Amount": "Deduction"}, inplace=True)
    display_df["Deduction"] = display_df["Deduction"].apply(
        lambda x: format_currency(x) if x else ""
    )
st.dataframe(display_df, use_container_width=True, hide_index=True)
