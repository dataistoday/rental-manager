"""
pages/03_maintenance_log.py — Maintenance Log

Log new issues (mold, plumbing, appliances, etc.), attach photos, assign contractors,
and update status. Each issue has a short ID for quick reference.
"""

import datetime
import streamlit as st
import pandas as pd

from sheets.maintenance import add_maintenance, update_maintenance_status, get_maintenance
from utils.cache import safe_get_maintenance, show_fetch_error
from utils.formatting import status_badge, priority_badge, format_currency, format_date
from drive.uploader import upload_image
from config import PROPERTIES, MAINTENANCE_STATUSES, MAINTENANCE_PRIORITIES

st.set_page_config(page_title="Maintenance Log", page_icon="🔧", layout="centered")
st.title("🔧 Maintenance Log")
st.caption("Track repairs from report to resolution.")

# ---------------------------------------------------------------------------
# Active issues
# ---------------------------------------------------------------------------
df, err = safe_get_maintenance()
show_fetch_error(err)

# Filter controls
col1, col2 = st.columns(2)
with col1:
    prop_filter = st.selectbox("Property", ["All"] + PROPERTIES, key="mnt_prop")
with col2:
    status_filter = st.selectbox("Status", ["All Open", "All"] + MAINTENANCE_STATUSES, key="mnt_status")

st.markdown("---")

filtered = df.copy() if df is not None and not df.empty else pd.DataFrame()

if not filtered.empty:
    if prop_filter != "All":
        filtered = filtered[filtered["property"] == prop_filter]
    if status_filter == "All Open":
        filtered = filtered[filtered["status"].isin(["Open", "In Progress"])]
    elif status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]

if filtered.empty:
    st.info("No matching issues. Log one below.", icon="ℹ️")
else:
    st.subheader(f"Issues ({len(filtered)})")

    # Sort: Emergency > High > Medium > Low, then by timestamp desc
    priority_order = {"Emergency": 0, "High": 1, "Medium": 2, "Low": 3}
    if "priority" in filtered.columns:
        filtered["_pri_ord"] = filtered["priority"].map(priority_order).fillna(9)
        filtered = filtered.sort_values(["_pri_ord", "timestamp"], ascending=[True, False])

    for sheet_idx, (_, row) in enumerate(filtered.iterrows()):
        issue_id = row.get("id", "—")
        title = row.get("issue_title", "Untitled")
        prop = row.get("property", "")
        status = row.get("status", "Open")
        priority = row.get("priority", "Medium")
        contractor = row.get("contractor", "")
        est_cost = row.get("estimated_cost", "")
        actual_cost = row.get("actual_cost", "")
        photo_urls = row.get("photo_urls", "")
        resolution = row.get("resolution_notes", "")
        ts = row.get("timestamp", "")

        label = f"{status_badge(status)} · `{issue_id}` · {prop} · **{title}**"
        with st.expander(label, expanded=(status == "Emergency")):
            st.markdown(f"{priority_badge(priority)} — reported {format_date(ts[:10]) if ts else '—'}")

            desc = row.get("description", "")
            if desc:
                st.write(desc)

            cols = st.columns(3)
            if contractor:
                cols[0].write(f"**Contractor:** {contractor}")
            if est_cost:
                cols[1].write(f"**Est. Cost:** {format_currency(est_cost)}")
            if actual_cost:
                cols[2].write(f"**Actual:** {format_currency(actual_cost)}")

            if photo_urls:
                for url in str(photo_urls).split(","):
                    url = url.strip()
                    if url:
                        st.markdown(f"[View Photo]({url})")

            if resolution:
                st.caption(f"Resolution: {resolution}")

            # Inline status update
            st.markdown("**Update Status**")
            new_status = st.selectbox(
                "Status", MAINTENANCE_STATUSES,
                index=MAINTENANCE_STATUSES.index(status) if status in MAINTENANCE_STATUSES else 0,
                key=f"status_{issue_id}",
            )
            new_actual = st.number_input(
                "Actual Cost ($)", min_value=0.0, step=10.0, format="%.2f",
                value=float(actual_cost) if actual_cost else 0.0,
                key=f"cost_{issue_id}",
            )
            new_resolution = st.text_input(
                "Resolution Notes", value=str(resolution),
                key=f"res_{issue_id}",
            )
            if st.button("Update", key=f"upd_{issue_id}", use_container_width=True):
                # Find the 1-based row index in the sheet (+2: 1 for header, 1 for 1-indexing)
                # We use the original (unfiltered) df to find position
                try:
                    orig_df = get_maintenance()
                    match = orig_df[orig_df["id"] == issue_id]
                    if match.empty:
                        st.error("Could not find this issue in the sheet.")
                    else:
                        row_idx = match.index[0] + 2  # 1-based + header offset
                        existing = orig_df.loc[match.index[0]].tolist()
                        update_maintenance_status(
                            row_index=row_idx,
                            existing_row=existing,
                            status=new_status,
                            actual_cost=new_actual if new_actual > 0 else None,
                            resolution_notes=new_resolution,
                        )
                        st.success("Updated!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

# ---------------------------------------------------------------------------
# Log new issue
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Log New Issue")

with st.form("maintenance_form", clear_on_submit=True):
    prop = st.selectbox("Property *", PROPERTIES)
    issue_title = st.text_input("Issue Title *", placeholder="e.g. Kitchen faucet dripping")
    description = st.text_area("Description", height=100, placeholder="Details, location, when it started…")

    col1, col2 = st.columns(2)
    with col1:
        priority = st.selectbox("Priority *", MAINTENANCE_PRIORITIES, index=1)
    with col2:
        status = st.selectbox("Initial Status", MAINTENANCE_STATUSES, index=0)

    contractor = st.text_input("Contractor (if known)")
    est_cost = st.number_input("Estimated Cost ($)", min_value=0.0, step=50.0, format="%.2f")

    # Photo upload
    photos = st.file_uploader(
        "Attach Photos", type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="Upload photos of the issue. They'll be saved to Google Drive.",
    )

    submitted = st.form_submit_button("Log Issue", use_container_width=True)
    if submitted:
        if not issue_title.strip():
            st.error("Issue Title is required.")
        else:
            try:
                # Upload photos first
                photo_url_list = []
                for photo in (photos or []):
                    ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"{prop.replace(' ', '_')}_{ts_str}_{photo.name}"
                    url = upload_image(photo.read(), fname, folder_key="maintenance")
                    photo_url_list.append(url)

                issue_id = add_maintenance(
                    property_name=prop,
                    issue_title=issue_title.strip(),
                    description=description.strip(),
                    status=status,
                    priority=priority,
                    contractor=contractor.strip(),
                    estimated_cost=est_cost,
                    photo_urls=", ".join(photo_url_list),
                )
                st.success(f"Issue logged! ID: `{issue_id}`")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
