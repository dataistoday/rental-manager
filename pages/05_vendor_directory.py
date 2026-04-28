"""
pages/05_vendor_directory.py — Vendor Directory

Filterable list of preferred Florida contractors.
Add new vendors via the form at the bottom.
"""

import streamlit as st
from utils.auth_gate import require_auth
from utils.cache import safe_get_vendors, show_fetch_error
from utils.formatting import format_phone
from sheets.vendors import add_vendor
from config import PROPERTIES, VENDOR_TRADES

require_auth()

st.set_page_config(page_title="Vendor Directory", page_icon="📋", layout="centered")
st.title("📋 Vendor Directory")
st.caption("Preferred contractors — filtered by property or trade.")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df, err = safe_get_vendors()
show_fetch_error(err)

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    prop_filter = st.selectbox("Property", ["All"] + PROPERTIES, key="vd_prop")
with col2:
    trade_filter = st.selectbox("Trade", ["All"] + VENDOR_TRADES, key="vd_trade")

# ---------------------------------------------------------------------------
# Vendor cards
# ---------------------------------------------------------------------------
st.markdown("---")

if df is None or df.empty:
    st.info("No vendors yet. Add your first contractor below.", icon="ℹ️")
else:
    filtered = df.copy()
    if prop_filter != "All":
        # "properties_served" may be "All" or comma-separated property names
        filtered = filtered[
            filtered["properties_served"].astype(str).str.contains(prop_filter, na=False)
            | filtered["properties_served"].astype(str).str.lower().eq("all")
        ]
    if trade_filter != "All":
        filtered = filtered[filtered["trade"] == trade_filter]

    if filtered.empty:
        st.info("No vendors match those filters.", icon="ℹ️")
    else:
        for _, row in filtered.iterrows():
            name = row.get("company_name", "Unknown")
            trade = row.get("trade", "")
            rating = row.get("rating", "")
            stars = "⭐" * int(rating) if str(rating).isdigit() else ""

            with st.expander(f"**{name}** — {trade}  {stars}", expanded=False):
                contact = row.get("contact_name", "")
                phone = format_phone(row.get("phone", ""))
                email = row.get("email", "")
                rate = row.get("hourly_rate", "")
                notes = row.get("notes", "")
                props = row.get("properties_served", "")
                last_used = row.get("last_used_date", "")

                if contact:
                    st.write(f"**Contact:** {contact}")
                if phone:
                    st.markdown(f"**Phone:** [{phone}](tel:{phone.replace(' ', '').replace('(','').replace(')','').replace('-','')})")
                if email:
                    st.markdown(f"**Email:** [{email}](mailto:{email})")
                if rate:
                    st.write(f"**Rate:** ${rate}/hr")
                if props:
                    st.write(f"**Serves:** {props}")
                if last_used:
                    st.write(f"**Last used:** {last_used}")
                if notes:
                    st.caption(f"Notes: {notes}")

# ---------------------------------------------------------------------------
# Add Vendor form
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Add Vendor")

with st.form("add_vendor_form", clear_on_submit=True):
    company = st.text_input("Company Name *")
    contact = st.text_input("Contact Name")
    col1, col2 = st.columns(2)
    with col1:
        phone = st.text_input("Phone")
    with col2:
        email = st.text_input("Email")
    col3, col4 = st.columns(2)
    with col3:
        trade = st.selectbox("Trade *", VENDOR_TRADES)
    with col4:
        rating = st.selectbox("Rating", ["", 5, 4, 3, 2, 1])

    props_served = st.multiselect("Properties Served", ["All"] + PROPERTIES, default=["All"])
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.0, step=5.0, format="%.2f")
    notes = st.text_area("Notes", height=80)

    submitted = st.form_submit_button("Add Vendor", use_container_width=True)
    if submitted:
        if not company.strip():
            st.error("Company Name is required.")
        else:
            try:
                add_vendor(
                    company_name=company.strip(),
                    contact_name=contact.strip(),
                    phone=phone.strip(),
                    email=email.strip(),
                    trade=trade,
                    properties_served=", ".join(props_served) if props_served else "All",
                    hourly_rate=hourly_rate,
                    rating=int(rating) if rating else 0,
                    notes=notes.strip(),
                )
                st.success(f"Vendor '{company}' added!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
