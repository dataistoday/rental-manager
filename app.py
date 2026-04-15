"""
app.py — Rental Portfolio Manager entry point.

Run locally:
    streamlit run app.py

The optional password gate is controlled by APP_PASSWORD in .env (local)
or st.secrets (Streamlit Cloud). Leave it blank/unset for open access.
"""

import os
import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load .env when running locally; no-op on Streamlit Cloud
load_dotenv()

st.set_page_config(
    page_title="Rental Manager",
    page_icon="🏠",
    layout="centered",          # single-column — ideal for mobile
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Optional password gate
# ---------------------------------------------------------------------------

def _get_app_password() -> str:
    """Return configured password, or empty string if none."""
    # st.secrets may not exist when running locally without a secrets.toml
    try:
        return st.secrets.get("APP_PASSWORD", "") or os.getenv("APP_PASSWORD", "")
    except Exception:
        return os.getenv("APP_PASSWORD", "")


def _check_password() -> bool:
    """Return True if the user is authenticated (or no password is set)."""
    pw = _get_app_password()
    if not pw:
        return True

    if st.session_state.get("authenticated"):
        return True

    st.title("🏠 Rental Manager")
    st.subheader("Sign In")
    entered = st.text_input("Password", type="password", placeholder="Enter password…")
    if st.button("Enter", use_container_width=True):
        if entered == pw:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Try again.")
    return False


if not _check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Home / dashboard
# ---------------------------------------------------------------------------

st.title("🏠 Rental Manager")
st.caption("Winter Garden (Regal) · Winter Garden (Charlotte) · Palm Harbor · Tampa")

st.markdown("---")

# ---------------------------------------------------------------------------
# Lease renewal alerts
# ---------------------------------------------------------------------------
try:
    from utils.cache import safe_get_tenants
    today = datetime.date.today()
    tenant_df, _ = safe_get_tenants()
    if tenant_df is not None and not tenant_df.empty:
        tenant_df = tenant_df.copy()
        tenant_df["lease_end"] = pd.to_datetime(tenant_df["lease_end"], errors="coerce")
        has_lease = tenant_df[tenant_df["lease_end"].notna()].copy()
        if not has_lease.empty:
            has_lease["entry_date"] = pd.to_datetime(has_lease["entry_date"], errors="coerce")
            # Latest lease record per property
            latest = (
                has_lease.sort_values("entry_date", ascending=False)
                .groupby("property", as_index=False)
                .first()
            )
            for _, row in latest.iterrows():
                lease_end = row["lease_end"].date()
                days_left = (lease_end - today).days
                prop = row["property"]
                if days_left < 0:
                    st.error(f"Lease expired: **{prop}** — {abs(days_left)} days ago", icon="🔴")
                elif days_left <= 30:
                    st.error(f"Lease expiring in **{days_left} days**: {prop}", icon="🔴")
                elif days_left <= 60:
                    st.warning(f"Lease expiring in **{days_left} days**: {prop}", icon="🟠")
                elif days_left <= 90:
                    st.warning(f"Lease expiring in **{days_left} days**: {prop}", icon="🟡")
except Exception:
    pass  # Never crash the home page over alert logic

st.markdown("---")

st.markdown(
    """
Use the **sidebar** (top-left ☰) to navigate between modules:

| Module | Purpose |
|---|---|
| 💸 Expense Capture | Scan receipts · log costs to Schedule E |
| 🚗 Mileage Tracker | Log trips · track IRS deductions |
| 🔧 Maintenance Log | Track repairs · manage contractors |
| 🛡️ Insurance Vault | Policy numbers · agent contacts |
| 📋 Vendor Directory | Preferred contractors by trade |
| 👤 Tenant Log | Interaction history · lease records |
| 🧾 Tax Summary | Schedule E deductions by year & property |
| 📅 Lease Renewals | Expiration alerts · renewal tracking |
| 🔍 Inspection Log | Move-in/out · annual inspections |
| ⚡ Utility Tracker | Bills by property · unpaid alerts |
| 📸 Property Photos | Zillow-ready listing photos by property |
"""
)

st.markdown("---")
st.caption(
    "Data is stored in Google Sheets and Google Drive. "
    "All expenses are categorised to IRS Schedule E for audit readiness."
)
