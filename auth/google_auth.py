"""
auth/google_auth.py

Dual-mode Google credential provider:
  - Local: reads credentials.json path from GOOGLE_CREDENTIALS_PATH env var
  - Streamlit Cloud: reads service account dict from st.secrets["GOOGLE_SERVICE_ACCOUNT"]

All other modules call get_gspread_client() and get_drive_service() — they never
touch secrets directly.
"""

import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_credentials() -> Credentials:
    """
    Try Streamlit secrets first (cloud deployment), then fall back to a local
    credentials.json file (local development).
    """
    # --- Cloud path: st.secrets has GOOGLE_SERVICE_ACCOUNT as a TOML table ---
    try:
        info = dict(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
        # st.secrets values are AttrDict; convert nested objects to plain dicts
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    except (KeyError, FileNotFoundError, AttributeError):
        pass

    # --- Local path: credentials.json on disk ---
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"Google credentials not found at '{creds_path}'.\n"
            "Set GOOGLE_CREDENTIALS_PATH in your .env file or place credentials.json "
            "in the project root. See .env.example for instructions."
        )
    return Credentials.from_service_account_file(creds_path, scopes=SCOPES)


@st.cache_resource(show_spinner=False)
def get_gspread_client() -> gspread.Client:
    """Return an authorised gspread client. Cached for the app session."""
    return gspread.authorize(_get_credentials())


@st.cache_resource(show_spinner=False)
def get_drive_service():
    """Return an authorised Google Drive v3 service. Cached for the app session."""
    return build("drive", "v3", credentials=_get_credentials())
