"""
pages/10_showings.py — Showing Tracker

Log prospective tenant showings by property.
"""

import datetime
import streamlit as st
from utils.cache import safe_get_showings, show_fetch_error
from sheets.showings import add_showing
from config import PROPERTIES

st.set_page_config(page_title="Showings", page_icon="🏡", layout="centered")
st.title("🏡 Showings")
st.caption("Track prospective tenant showings by property.")

# ---------------------------------------------------------------------------
# Log a showing
# ---------------------------------------------------------------------------
with st.form("add_showing_form", clear_on_submit=True):
    st.subheader("Log a Showing")

    name = st.text_input("Prospect Name *")
    property_ = st.selectbox("Property *", ["All"] + PROPERTIES)

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", value=datetime.date.today())
    with col2:
        time = st.time_input("Time", value=datetime.time(10, 0), step=1800)

    location_found = st.selectbox(
        "Where did they find the listing?",
        ["", "Zillow", "Facebook Marketplace", "Craigslist", "Referral", "Avail", "Other"],
    )

    notes = st.text_area("Notes", height=100, placeholder="Impressions, follow-up needed, pet, income, etc.")

    submitted = st.form_submit_button("Save Showing", use_container_width=True)
    if submitted:
        if not name.strip():
            st.error("Prospect Name is required.")
        else:
            try:
                add_showing(
                    property=property_,
                    name=name.strip(),
                    location_found=location_found,
                    date=date.isoformat(),
                    time=time.strftime("%I:%M %p"),
                    notes=notes.strip(),
                )
                st.success(f"Showing logged for {name.strip()}!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")

# ---------------------------------------------------------------------------
# Showing history
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Showing History")

df, err = safe_get_showings()
show_fetch_error(err)

if df is None or df.empty:
    st.info("No showings logged yet.", icon="ℹ️")
else:
    prop_filter = st.selectbox("Filter by property", ["All"] + PROPERTIES, key="show_prop")
    if prop_filter != "All":
        df = df[df["property"] == prop_filter]

    if df.empty:
        st.info("No showings for that property.", icon="ℹ️")
    else:
        display = df[["date", "time", "property", "name", "location_found", "notes"]].copy()
        display.columns = ["Date", "Time", "Property", "Name", "Found Via", "Notes"]
        display = display.sort_values("Date", ascending=False)
        st.dataframe(display, use_container_width=True, hide_index=True)
