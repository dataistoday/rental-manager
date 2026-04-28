"""
pages/11_property_photos.py — Property Photos

Upload and browse Zillow-ready listing photos, organized by property.
Each property gets its own subfolder in Google Drive (auto-created on first upload).
"""

import datetime
import streamlit as st
from utils.auth_gate import require_auth

from drive.uploader import upload_photo_for_property, list_property_photos
from config import PROPERTIES

require_auth()

st.set_page_config(page_title="Property Photos", page_icon="📸", layout="centered")
st.title("📸 Property Photos")
st.caption("Listing and Zillow-ready photos, organized by property in Google Drive.")

prop = st.selectbox("Property", PROPERTIES)

st.markdown("---")

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
st.subheader("Upload Photos")

uploaded_files = st.file_uploader(
    "Select photos to upload",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Upload multiple at once. Each goes into the property's Drive subfolder.",
)

if uploaded_files:
    if st.button(f"Upload {len(uploaded_files)} photo(s) to {prop}", use_container_width=True):
        results = []
        errors = []
        progress = st.progress(0, text="Uploading…")

        for i, f in enumerate(uploaded_files):
            try:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_prop = prop.replace(" ", "_").replace("(", "").replace(")", "")
                fname = f"{safe_prop}_{ts}_{f.name}"
                url = upload_photo_for_property(f.read(), fname, prop)
                results.append((f.name, url))
            except Exception as e:
                errors.append(f"{f.name}: {e}")
            progress.progress((i + 1) / len(uploaded_files), text=f"Uploading {f.name}…")

        progress.empty()

        if results:
            st.success(f"Uploaded {len(results)} photo(s) to **{prop}**.")
        for name, url in results:
            st.markdown(f"- [{name}]({url})")
        for err in errors:
            st.error(err)

st.markdown("---")

# ---------------------------------------------------------------------------
# Browse existing photos
# ---------------------------------------------------------------------------
st.subheader(f"Photos — {prop}")

with st.spinner("Loading photos from Drive…"):
    try:
        photos = list_property_photos(prop)
    except Exception as e:
        st.error(f"Could not load photos: {e}")
        photos = []

if not photos:
    st.info("No photos uploaded yet for this property.", icon="ℹ️")
else:
    st.caption(f"{len(photos)} photo(s) in Drive")
    cols = st.columns(3)
    for i, photo in enumerate(photos):
        thumb_url = f"https://lh3.googleusercontent.com/d/{photo['id']}"
        with cols[i % 3]:
            st.markdown(
                f'<a href="{photo["url"]}" target="_blank">'
                f'<img src="{thumb_url}" style="width:100%;border-radius:6px;margin-bottom:6px;">'
                f'</a>',
                unsafe_allow_html=True,
            )
            st.caption(photo["name"])

st.markdown("---")
st.caption(
    "Photos are stored in Google Drive under **Property Photos / {property name}**. "
    "The subfolder is created automatically on first upload. "
    "Add the parent folder ID as `DRIVE_FOLDER_PHOTOS` in your `.env` file."
)
