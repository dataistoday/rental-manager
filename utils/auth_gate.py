import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def require_auth():
    """Call at the top of every page. Stops rendering if not authenticated."""
    try:
        pw = st.secrets.get("APP_PASSWORD", "") or os.getenv("APP_PASSWORD", "")
    except Exception:
        pw = os.getenv("APP_PASSWORD", "")

    if not pw:
        return  # No password configured — open access

    if st.session_state.get("authenticated"):
        return

    st.title("🏠 Rental Manager")
    st.subheader("Sign In")
    entered = st.text_input("Password", type="password", placeholder="Enter password…")
    if st.button("Enter", use_container_width=True):
        if entered == pw:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Try again.")
    st.stop()
