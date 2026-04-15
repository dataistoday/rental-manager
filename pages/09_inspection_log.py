"""
pages/09_inspection_log.py — Inspection Log

Log move-in/move-out, annual, and ad-hoc property inspections.
Records condition, notes, action items, and photos to Drive.
"""

import datetime
import streamlit as st
import pandas as pd

from sheets.inspections import add_inspection, get_inspections
from utils.cache import safe_get_inspections, show_fetch_error
from utils.formatting import format_date
from drive.uploader import upload_image
from config import PROPERTIES, INSPECTION_TYPES, INSPECTION_CONDITIONS

st.set_page_config(page_title="Inspection Log", page_icon="🔍", layout="centered")
st.title("🔍 Inspection Log")
st.caption("Move-in, move-out, annual, and ad-hoc property inspections.")

# ---------------------------------------------------------------------------
# Inspection history
# ---------------------------------------------------------------------------
df, err = safe_get_inspections()
show_fetch_error(err)

col1, col2 = st.columns(2)
with col1:
    prop_filter = st.selectbox("Property", ["All"] + PROPERTIES, key="insp_prop")
with col2:
    type_filter = st.selectbox("Type", ["All"] + INSPECTION_TYPES, key="insp_type")

st.markdown("---")

filtered = df.copy() if df is not None and not df.empty else pd.DataFrame()

if not filtered.empty:
    if prop_filter != "All":
        filtered = filtered[filtered["property"] == prop_filter]
    if type_filter != "All":
        filtered = filtered[filtered["inspection_type"] == type_filter]
    filtered = filtered.sort_values("inspection_date", ascending=False, na_position="last")

_CONDITION_BADGE = {
    "Excellent": "🟢 Excellent",
    "Good":      "🟢 Good",
    "Fair":      "🟡 Fair",
    "Poor":      "🔴 Poor",
}

if filtered.empty:
    st.info("No inspections logged yet. Add one below.", icon="ℹ️")
else:
    st.subheader(f"Inspections ({len(filtered)})")
    for _, row in filtered.iterrows():
        insp_id    = row.get("id", "—")
        prop       = row.get("property", "")
        insp_type  = row.get("inspection_type", "")
        insp_date  = row.get("inspection_date", "")
        inspector  = row.get("inspector", "")
        condition  = row.get("condition_overall", "")
        notes      = row.get("notes", "")
        actions    = row.get("action_items", "")
        photos     = row.get("photo_urls", "")

        cond_badge = _CONDITION_BADGE.get(condition, condition)
        label = f"`{insp_id}` · {prop} · {insp_type} · {format_date(insp_date)}"
        if condition:
            label += f" · {cond_badge}"

        with st.expander(label):
            if inspector:
                st.write(f"**Inspector:** {inspector}")
            if notes:
                st.write(f"**Notes:** {notes}")
            if actions:
                st.warning(f"**Action Items:** {actions}", icon="📋")
            if photos:
                for url in str(photos).split(","):
                    url = url.strip()
                    if url:
                        st.markdown(f"[View Photo]({url})")

# ---------------------------------------------------------------------------
# Log new inspection
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Log New Inspection")

with st.form("inspection_form", clear_on_submit=True):
    prop = st.selectbox("Property *", PROPERTIES)

    col1, col2 = st.columns(2)
    with col1:
        insp_type = st.selectbox("Inspection Type *", INSPECTION_TYPES)
    with col2:
        insp_date = st.date_input("Inspection Date *", value=datetime.date.today())

    col3, col4 = st.columns(2)
    with col3:
        inspector = st.text_input("Inspector / Done By", placeholder="Your name or contractor")
    with col4:
        condition = st.selectbox("Overall Condition", [""] + INSPECTION_CONDITIONS)

    notes = st.text_area(
        "Notes",
        height=100,
        placeholder="General condition, observations, tenant present?…",
    )
    action_items = st.text_area(
        "Action Items",
        height=80,
        placeholder="Items that need follow-up, repairs to schedule…",
    )

    photos = st.file_uploader(
        "Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    submitted = st.form_submit_button("Save Inspection", use_container_width=True)
    if submitted:
        try:
            photo_urls = []
            for photo in (photos or []):
                ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"{prop.replace(' ', '_')}_{insp_type.replace(' ', '_')}_{ts_str}_{photo.name}"
                url = upload_image(photo.read(), fname, folder_key="maintenance")
                photo_urls.append(url)

            insp_id = add_inspection(
                property_name=prop,
                inspection_type=insp_type,
                inspection_date=insp_date,
                inspector=inspector.strip(),
                condition_overall=condition,
                notes=notes.strip(),
                action_items=action_items.strip(),
                photo_urls=", ".join(photo_urls),
            )
            st.success(f"Inspection saved! ID: `{insp_id}`")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save: {e}")
