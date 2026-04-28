"""
pages/04_insurance_vault.py — Insurance Vault

Read-only reference cards: one per policy per property.
Populated manually in Google Sheets; read from the app.
"""

import streamlit as st
from utils.auth_gate import require_auth
from utils.cache import safe_get_insurance, show_fetch_error
from utils.formatting import format_currency, format_date, format_phone
from config import PROPERTIES

require_auth()

st.set_page_config(page_title="Insurance Vault", page_icon="🛡️", layout="centered")
st.title("🛡️ Insurance Vault")
st.caption("Policy numbers and agent contacts — always one tap away.")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df, err = safe_get_insurance()
show_fetch_error(err)

if df is None or df.empty:
    st.info(
        "No insurance records yet. Add them directly in the **Insurance** tab of your "
        "Google Sheet — they'll appear here automatically.",
        icon="ℹ️",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Property filter
# ---------------------------------------------------------------------------
all_props = ["All Properties"] + PROPERTIES
selected = st.selectbox("Property", all_props)

if selected != "All Properties":
    df = df[df["property"] == selected]

if df.empty:
    st.warning(f"No insurance records found for {selected}.")
    st.stop()

# ---------------------------------------------------------------------------
# Policy cards
# ---------------------------------------------------------------------------
st.markdown("---")

for _, row in df.iterrows():
    prop = row.get("property", "")
    insurer = row.get("insurer", "")
    coverage = row.get("coverage_type", "")
    header = f"**{prop}** — {insurer}" + (f" ({coverage})" if coverage else "")
    with st.expander(header, expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Policy Number**")
            st.code(row.get("policy_number", "—"), language=None)
            st.markdown("**Annual Premium**")
            st.write(format_currency(row.get("premium_annual", "")) or "—")
            st.markdown("**Renewal Date**")
            st.write(format_date(row.get("renewal_date", "")) or "—")
        with c2:
            st.markdown("**Agent**")
            st.write(row.get("agent_name", "—"))
            st.markdown("**Phone**")
            phone = format_phone(row.get("agent_phone", ""))
            if phone:
                st.markdown(f"[{phone}](tel:{phone.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')})")
            else:
                st.write("—")
            st.markdown("**Email**")
            email = row.get("agent_email", "")
            if email:
                st.markdown(f"[{email}](mailto:{email})")
            else:
                st.write("—")

        doc_url = row.get("doc_url", "")
        if doc_url:
            st.link_button("Open Policy Document", doc_url, use_container_width=True)

        notes = row.get("notes", "")
        if notes:
            st.caption(f"Notes: {notes}")
