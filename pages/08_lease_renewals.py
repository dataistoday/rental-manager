"""
pages/08_lease_renewals.py — Lease Renewal Alerts

Reads lease_end dates from the Tenants sheet and surfaces expiring leases.
Shows a color-coded alert for each property based on days remaining.
"""

import datetime
import pandas as pd
import streamlit as st
from utils.auth_gate import require_auth

from utils.cache import safe_get_tenants, show_fetch_error
from utils.formatting import format_date, format_currency
from config import PROPERTIES

require_auth()

st.set_page_config(page_title="Lease Renewals", page_icon="📅", layout="centered")
st.title("📅 Lease Renewals")
st.caption("Upcoming lease expirations across all properties.")

today = datetime.date.today()

# ---------------------------------------------------------------------------
# Load tenant data
# ---------------------------------------------------------------------------
df, err = safe_get_tenants()
show_fetch_error(err)

# ---------------------------------------------------------------------------
# Find the most recent lease record per property
# (a property may have many log entries; we want the latest one with a lease_end)
# ---------------------------------------------------------------------------
leases: list[dict] = []

if df is not None and not df.empty:
    df = df.copy()
    df["lease_end"] = pd.to_datetime(df["lease_end"], errors="coerce")
    df["lease_start"] = pd.to_datetime(df["lease_start"], errors="coerce")
    df["entry_date"] = pd.to_datetime(df["entry_date"], errors="coerce")

    # Only rows that have a valid lease_end
    has_lease = df[df["lease_end"].notna()].copy()

    for prop in PROPERTIES:
        prop_rows = has_lease[has_lease["property"] == prop]
        if prop_rows.empty:
            leases.append({"property": prop, "status": "no_data"})
            continue

        # Most recent entry with a lease_end
        latest = prop_rows.sort_values("entry_date", ascending=False).iloc[0]
        lease_end = latest["lease_end"].date()
        lease_start = latest["lease_start"].date() if pd.notna(latest["lease_start"]) else None
        days_left = (lease_end - today).days
        tenant = latest.get("tenant_name", "")
        rent = latest.get("monthly_rent", "")

        leases.append({
            "property":    prop,
            "tenant":      tenant,
            "lease_start": lease_start,
            "lease_end":   lease_end,
            "days_left":   days_left,
            "monthly_rent": rent,
            "status":      "active" if days_left >= 0 else "expired",
        })
else:
    for prop in PROPERTIES:
        leases.append({"property": prop, "status": "no_data"})

# ---------------------------------------------------------------------------
# Sort: most urgent first
# ---------------------------------------------------------------------------
def _sort_key(l):
    if l["status"] == "no_data":
        return 9999
    if l["status"] == "expired":
        return -9999
    return l["days_left"]

leases.sort(key=_sort_key)

# ---------------------------------------------------------------------------
# Alert banner — leases expiring within 90 days
# ---------------------------------------------------------------------------
urgent = [l for l in leases if l.get("days_left") is not None and 0 <= l["days_left"] <= 90]
expired = [l for l in leases if l.get("status") == "expired"]

if expired:
    props = ", ".join(l["property"] for l in expired)
    st.error(f"Lease expired: **{props}** — renew or start move-out process.", icon="🔴")

if urgent:
    for l in urgent:
        days = l["days_left"]
        icon = "🔴" if days <= 30 else "🟡"
        st.warning(
            f"{icon} **{l['property']}** — lease ends {format_date(l['lease_end'])} "
            f"(**{days} days**)",
            icon="⚠️",
        )

if not expired and not urgent:
    st.success("No leases expiring within the next 90 days.", icon="✅")

st.markdown("---")

# ---------------------------------------------------------------------------
# Property cards
# ---------------------------------------------------------------------------
st.subheader("All Properties")

for l in leases:
    prop = l["property"]
    status = l["status"]

    if status == "no_data":
        with st.expander(f"⚪ {prop} — no lease data"):
            st.caption("No tenant record with a lease end date found for this property.")
        continue

    days_left = l["days_left"]
    lease_end = l["lease_end"]

    if status == "expired":
        badge = "🔴 Expired"
    elif days_left <= 30:
        badge = "🔴 Expiring Soon"
    elif days_left <= 60:
        badge = "🟠 Expiring"
    elif days_left <= 90:
        badge = "🟡 Due Soon"
    else:
        badge = "🟢 Active"

    label = f"{badge} · {prop}"
    with st.expander(label, expanded=(days_left is not None and days_left <= 30)):
        col1, col2 = st.columns(2)
        col1.metric("Lease End", format_date(lease_end))
        if status == "expired":
            col2.metric("Status", f"Expired {abs(days_left)} days ago")
        else:
            col2.metric("Days Remaining", days_left)

        if l.get("tenant"):
            st.write(f"**Tenant:** {l['tenant']}")
        if l.get("lease_start"):
            st.write(f"**Lease Start:** {format_date(l['lease_start'])}")
        if l.get("monthly_rent"):
            try:
                st.write(f"**Monthly Rent:** {format_currency(float(l['monthly_rent']))}")
            except (TypeError, ValueError):
                pass

st.markdown("---")
st.caption(
    "Lease dates are pulled from the Tenants sheet. "
    "To update a lease, add a new entry in the Tenant Log page."
)
