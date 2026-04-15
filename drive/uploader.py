"""
drive/uploader.py

Upload files to Google Drive and return a shareable link.
All uploads land in a pre-configured folder (receipts, maintenance, documents).
"""

import os
import io
import streamlit as st
from googleapiclient.http import MediaIoBaseUpload

from auth.google_auth import get_drive_service
from config import DRIVE_FOLDERS


def _resolve_folder_id(folder_key: str) -> str:
    """
    Look up the Drive folder ID for the given key.
    Prefers environment variables over config.py defaults.
    """
    env_map = {
        "receipts":    "DRIVE_FOLDER_RECEIPTS",
        "maintenance": "DRIVE_FOLDER_MAINTENANCE",
        "documents":   "DRIVE_FOLDER_DOCUMENTS",
        "photos":      "DRIVE_FOLDER_PHOTOS",
    }
    env_var = env_map.get(folder_key, "")
    folder_id = (
        os.getenv(env_var)
        or st.secrets.get(env_var, "")
        or DRIVE_FOLDERS.get(folder_key, "")
    )
    if not folder_id or folder_id == "REPLACE_WITH_DRIVE_FOLDER_ID":
        raise ValueError(
            f"Drive folder ID for '{folder_key}' is not configured. "
            f"Set {env_var} in your .env file or Streamlit secrets."
        )
    return folder_id


def get_or_create_subfolder(parent_folder_id: str, subfolder_name: str) -> str:
    """
    Return the Drive folder ID for subfolder_name inside parent_folder_id.
    Creates the subfolder if it doesn't exist yet.
    """
    service = get_drive_service()

    # Search for an existing folder with this name under the parent
    query = (
        f"name='{subfolder_name}' "
        f"and '{parent_folder_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create it
    metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_photo_for_property(
    image_bytes: bytes,
    filename: str,
    property_name: str,
) -> str:
    """
    Upload a Zillow/listing photo to Drive, organized into a per-property subfolder.
    Subfolder is created automatically if it doesn't exist.

    Returns a shareable URL.
    """
    service = get_drive_service()
    parent_id = _resolve_folder_id("photos")
    folder_id = get_or_create_subfolder(parent_id, property_name)

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "jpg"
    mime_type = "image/png" if ext == "png" else "image/jpeg"

    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type, resumable=True)

    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    file_id = uploaded.get("id")

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"


def list_property_photos(property_name: str) -> list[dict]:
    """
    Return a list of {name, url, id} dicts for all photos in the property subfolder.
    Returns an empty list if the folder doesn't exist yet.
    """
    service = get_drive_service()
    parent_id = _resolve_folder_id("photos")

    # Find the subfolder (don't create if missing — nothing to list)
    query = (
        f"name='{property_name}' "
        f"and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    folders = results.get("files", [])
    if not folders:
        return []

    folder_id = folders[0]["id"]
    photo_query = (
        f"'{folder_id}' in parents "
        f"and mimeType contains 'image/' "
        f"and trashed=false"
    )
    photo_results = service.files().list(
        q=photo_query,
        fields="files(id, name, createdTime)",
        orderBy="createdTime desc",
    ).execute()

    return [
        {
            "name": f["name"],
            "url":  f"https://drive.google.com/file/d/{f['id']}/view",
            "id":   f["id"],
        }
        for f in photo_results.get("files", [])
    ]


def upload_file(
    file_bytes: bytes,
    filename: str,
    folder_key: str = "receipts",
    mime_type: str = "application/octet-stream",
) -> str:
    """
    Upload bytes to the specified Google Drive folder.

    Args:
        file_bytes:  Raw bytes of the file to upload.
        filename:    Name to give the file in Drive.
        folder_key:  One of "receipts", "maintenance", or "documents".
        mime_type:   MIME type (e.g. "image/jpeg", "application/pdf").

    Returns:
        A shareable URL string (anyone with the link can view).
    """
    service = get_drive_service()
    folder_id = _resolve_folder_id(folder_key)

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)

    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    file_id = uploaded.get("id")

    # Make the file viewable by anyone with the link
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"


def upload_image(
    image_bytes: bytes,
    filename: str,
    folder_key: str = "receipts",
) -> str:
    """Convenience wrapper for JPEG/PNG image uploads."""
    mime_type = "image/jpeg" if filename.lower().endswith(".jpg") else "image/png"
    return upload_file(image_bytes, filename, folder_key, mime_type)


def upload_pdf(file_bytes: bytes, filename: str, folder_key: str = "documents") -> str:
    """Convenience wrapper for PDF uploads."""
    return upload_file(file_bytes, filename, folder_key, "application/pdf")
