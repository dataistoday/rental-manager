"""
pages/13_vehicle_snapshots.py — Vehicle Year-End Snapshot

Captures the per-vehicle, per-year odometer readings the IRS needs for
Form 4562 Part V (Listed Property). Cross-references the Mileage tab to
compute business miles and business-use percentage automatically.
"""

import datetime
import pandas as pd
import streamlit as st

from utils.cache import safe_get_vehicle_snapshots, safe_get_mileage, show_fetch_error
from sheets.vehicle_snapshots import add_vehicle_snapshot
from config import VEHICLES

st.set_page_config(page_title="Vehicle Snapshots", page_icon="🚙", layout="centered")
st.title("🚙 Vehicle Year-End Snapshot")
st.caption(
    "Once a year (early January is fine), record each vehicle's odometer. "
    "Combined with your Mileage log, this produces the business-use percentage "
    "your CPA needs for Form 4562 Part V."
)

# ---------------------------------------------------------------------------
# Form: log a snapshot
# ---------------------------------------------------------------------------
current_year = datetime.date.today().year

with st.form("vehicle_snapshot_form", clear_on_submit=True):
    st.subheader("Log Snapshot")

    col1, col2 = st.columns(2)
    with col1:
        tax_year = st.selectbox(
            "Tax Year *",
            options=list(range(current_year, current_year - 6, -1)),
            index=0,
        )
    with col2:
        vehicle = st.selectbox("Vehicle *", VEHICLES)

    col3, col4 = st.columns(2)
    with col3:
        jan_1_odo = st.number_input(
            "Jan 1 Odometer", min_value=0, step=1, value=0,
            help="Reading on January 1 of the tax year.",
        )
    with col4:
        dec_31_odo = st.number_input(
            "Dec 31 Odometer", min_value=0, step=1, value=0,
            help="Reading on December 31 of the tax year. Can be filled in later.",
        )

    placed_in_service = st.date_input(
        "Date placed in service for rental business",
        value=datetime.date(current_year, 1, 1),
        help="When you first started using this vehicle for rental property work.",
    )

    has_other = st.radio(
        "Do you have another vehicle for personal use?",
        options=["Yes", "No"],
        horizontal=True,
        help="The IRS asks this on Form 4562 Part V to check whether the "
             "rental vehicle is also your only personal vehicle.",
    )

    notes = st.text_area("Notes", height=70, placeholder="Any context — e.g. sold mid-year, new vehicle, etc.")

    submitted = st.form_submit_button("Save Snapshot", use_container_width=True)
    if submitted:
        if dec_31_odo and jan_1_odo and dec_31_odo < jan_1_odo:
            st.error("Dec 31 odometer must be ≥ Jan 1 odometer.")
        else:
            try:
                add_vehicle_snapshot(
                    tax_year=tax_year,
                    vehicle=vehicle,
                    jan_1_odometer=jan_1_odo,
                    dec_31_odometer=dec_31_odo,
                    placed_in_service_date=placed_in_service.isoformat(),
                    has_other_personal_vehicle=has_other,
                    notes=notes.strip(),
                )
                st.success(f"Saved {tax_year} snapshot for {vehicle}.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")

# ---------------------------------------------------------------------------
# History + business-use % calculation
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Snapshot History — with business-use %")

snap_df, snap_err = safe_get_vehicle_snapshots()
mil_df, mil_err = safe_get_mileage()
show_fetch_error(snap_err or mil_err)

if snap_df is None or snap_df.empty:
    st.info("No snapshots logged yet. Log one above.", icon="ℹ️")
    st.stop()

snap = snap_df.copy()
snap["tax_year"] = pd.to_numeric(snap["tax_year"], errors="coerce").astype("Int64")
snap["jan_1_odometer"] = pd.to_numeric(snap["jan_1_odometer"], errors="coerce")
snap["dec_31_odometer"] = pd.to_numeric(snap["dec_31_odometer"], errors="coerce")
snap["total_miles"] = (snap["dec_31_odometer"] - snap["jan_1_odometer"]).fillna(0).clip(lower=0)

# Business miles per (year, vehicle) from Mileage tab
biz_lookup: dict[tuple, float] = {}
if mil_df is not None and not mil_df.empty:
    m = mil_df.copy()
    m["miles"] = pd.to_numeric(m["miles"], errors="coerce").fillna(0)
    m["date"] = pd.to_datetime(m["date"], errors="coerce")
    m["year"] = m["date"].dt.year
    if "vehicle" in m.columns:
        grouped = m.groupby(["year", "vehicle"])["miles"].sum()
        biz_lookup = grouped.to_dict()

def _biz_miles(row) -> float:
    yr = row["tax_year"]
    veh = row["vehicle"]
    if pd.isna(yr):
        return 0.0
    return float(biz_lookup.get((int(yr), veh), 0.0))

snap["business_miles"] = snap.apply(_biz_miles, axis=1)
snap["business_use_pct"] = snap.apply(
    lambda r: (r["business_miles"] / r["total_miles"] * 100) if r["total_miles"] > 0 else 0.0,
    axis=1,
)

display = snap[[
    "tax_year", "vehicle", "jan_1_odometer", "dec_31_odometer",
    "total_miles", "business_miles", "business_use_pct",
    "placed_in_service_date", "has_other_personal_vehicle", "notes",
]].copy()

display.columns = [
    "Tax Year", "Vehicle", "Jan 1 Odo", "Dec 31 Odo",
    "Total Miles", "Business Miles", "Business %",
    "In Service", "Other Personal Vehicle?", "Notes",
]
display["Total Miles"] = display["Total Miles"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
display["Business Miles"] = display["Business Miles"].apply(lambda x: f"{x:,.0f}")
display["Business %"] = display["Business %"].apply(lambda x: f"{x:.1f}%")
display["Jan 1 Odo"] = display["Jan 1 Odo"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
display["Dec 31 Odo"] = display["Dec 31 Odo"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

display = display.sort_values(["Tax Year", "Vehicle"], ascending=[False, True])
st.dataframe(display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Reminder
# ---------------------------------------------------------------------------
st.markdown("---")
st.info(
    "💡 **Workflow:** Log the Jan 1 odometer in early January (set Dec 31 to 0 for now). "
    "Come back at year-end and add a fresh row with both readings filled in. "
    "Or log Jan 1 only now, and update the Sheet directly with the Dec 31 reading later.",
    icon="💡",
)
