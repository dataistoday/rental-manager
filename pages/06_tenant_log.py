"""
pages/06_tenant_log.py — Tenant Log

Per-property chronological history of tenant interactions, legal notices,
lease details, and payment records. Critical for eviction protection.
"""

import datetime
import streamlit as st

from sheets.tenants import add_tenant_log
from utils.cache import safe_get_tenants, show_fetch_error
from utils.formatting import format_currency, format_date
from config import PROPERTIES, ENTRY_TYPES

st.set_page_config(page_title="Tenant Log", page_icon="👤", layout="centered")
st.title("👤 Tenant Log")
st.caption("Chronological record of tenant interactions and lease history.")

# ---------------------------------------------------------------------------
# Property selector (drives both log view and new-entry form)
# ---------------------------------------------------------------------------
selected_prop = st.selectbox("Property", PROPERTIES, key="tl_prop")

# ---------------------------------------------------------------------------
# Log history for selected property
# ---------------------------------------------------------------------------
df, err = safe_get_tenants()
show_fetch_error(err)

st.markdown("---")
st.subheader(f"History — {selected_prop}")

prop_df = df[df["property"] == selected_prop].copy() if df is not None and not df.empty else None

ENTRY_ICONS = {
    "Legal Notice":       "⚖️",
    "Payment":            "💵",
    "Maintenance Request": "🔧",
    "Lease Renewal":      "📄",
    "Move-In":            "🏠",
    "Move-Out":           "📦",
    "Note":               "📝",
    "Other":              "📌",
}

if prop_df is None or prop_df.empty:
    st.info("No entries for this property yet. Add the first one below.", icon="ℹ️")
else:
    # Sort newest-first
    if "entry_date" in prop_df.columns:
        prop_df = prop_df.sort_values("entry_date", ascending=False)

    for _, row in prop_df.iterrows():
        entry_type = row.get("entry_type", "Note")
        icon = ENTRY_ICONS.get(entry_type, "📌")
        entry_date = format_date(row.get("entry_date", ""))
        subject = row.get("subject", "")
        tenant = row.get("tenant_name", "")
        header = f"{icon} **{entry_date}** · {entry_type}"
        if tenant:
            header += f" · {tenant}"

        with st.expander(header, expanded=False):
            if subject:
                st.markdown(f"**{subject}**")
            body = row.get("body", "")
            if body:
                st.write(body)

            # Lease info if present
            lease_start = row.get("lease_start", "")
            lease_end = row.get("lease_end", "")
            rent = row.get("monthly_rent", "")
            deposit = row.get("security_deposit", "")

            if any([lease_start, lease_end, rent, deposit]):
                cols = st.columns(4)
                if lease_start:
                    cols[0].metric("Lease Start", format_date(lease_start))
                if lease_end:
                    cols[1].metric("Lease End", format_date(lease_end))
                if rent:
                    cols[2].metric("Rent/mo", format_currency(rent))
                if deposit:
                    cols[3].metric("Deposit", format_currency(deposit))

            doc_url = row.get("doc_url", "")
            if doc_url:
                st.link_button("Open Document", doc_url, use_container_width=True)

# ---------------------------------------------------------------------------
# New entry form
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Add Entry")

with st.form("tenant_log_form", clear_on_submit=True):
    tenant_name = st.text_input("Tenant Name *")
    col1, col2 = st.columns(2)
    with col1:
        entry_type = st.selectbox("Entry Type *", ENTRY_TYPES)
    with col2:
        entry_date = st.date_input("Date *", value=datetime.date.today())

    subject = st.text_input("Subject / Title *", placeholder="e.g. Late rent notice served")
    body = st.text_area(
        "Details",
        height=120,
        placeholder="Full description, conversation notes, notice content…",
    )

    # Lease fields — only show when relevant
    show_lease = st.checkbox("Include lease details", value=False)
    lease_start = lease_end = monthly_rent = security_deposit = None
    if show_lease:
        col3, col4 = st.columns(2)
        with col3:
            lease_start = st.date_input("Lease Start")
        with col4:
            lease_end = st.date_input("Lease End")
        col5, col6 = st.columns(2)
        with col5:
            monthly_rent = st.number_input("Monthly Rent ($)", min_value=0.0, step=50.0, format="%.2f")
        with col6:
            security_deposit = st.number_input("Security Deposit ($)", min_value=0.0, step=50.0, format="%.2f")

    doc_url = st.text_input("Document URL (Google Drive link)", placeholder="https://drive.google.com/…")

    submitted = st.form_submit_button("Save Entry", use_container_width=True)
    if submitted:
        errors = []
        if not tenant_name.strip():
            errors.append("Tenant Name is required.")
        if not subject.strip():
            errors.append("Subject is required.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                add_tenant_log(
                    property_name=selected_prop,
                    tenant_name=tenant_name.strip(),
                    entry_type=entry_type,
                    entry_date=entry_date,
                    subject=subject.strip(),
                    body=body.strip(),
                    lease_start=lease_start.isoformat() if lease_start else "",
                    lease_end=lease_end.isoformat() if lease_end else "",
                    monthly_rent=monthly_rent or 0.0,
                    security_deposit=security_deposit or 0.0,
                    doc_url=doc_url.strip(),
                )
                st.success("Entry saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
