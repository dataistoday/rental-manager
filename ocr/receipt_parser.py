"""
ocr/receipt_parser.py

Uses the Veryfi API to extract structured data from receipt images:
  - vendor (merchant name)
  - date
  - amount (total)

Veryfi is a commercial receipt OCR API (~$0.08/receipt) that dramatically
outperforms local OCR on real-world receipts (crumpled, dim lighting, thermal paper).

Requires in .env (or st.secrets):
  VERYFI_CLIENT_ID
  VERYFI_CLIENT_SECRET
  VERYFI_API_KEY

Sign up at veryfi.com — free credits to start, pay-per-receipt after.

Falls back gracefully to an empty result if credentials are missing or the
API call fails — the user always fills in the form manually as a fallback.
"""

import os
import base64
import datetime
import streamlit as st

try:
    from veryfi import Client as VeryfiClient
    VERYFI_INSTALLED = True
except ImportError:
    VERYFI_INSTALLED = False


def _get_credentials() -> tuple[str, str, str] | tuple[None, None, None]:
    """Return (client_id, client_secret, api_key) from env or st.secrets."""
    def _get(key: str) -> str:
        try:
            return st.secrets.get(key, "") or os.getenv(key, "")
        except Exception:
            return os.getenv(key, "")

    client_id     = _get("VERYFI_CLIENT_ID")
    client_secret = _get("VERYFI_CLIENT_SECRET")
    api_key       = _get("VERYFI_API_KEY")

    if client_id and client_secret and api_key:
        return client_id, client_secret, api_key
    return None, None, None


def _parse_date(date_str: str | None) -> datetime.date | None:
    """Convert Veryfi date string (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD) to date."""
    if not date_str:
        return None
    try:
        return datetime.date.fromisoformat(date_str[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Expose this so pages/01_expense_capture.py can check whether to show the scanner
OCR_AVAILABLE = VERYFI_INSTALLED

def parse_receipt(image_bytes: bytes, file_name: str = "receipt.jpg") -> dict:
    """
    Send the receipt image to Veryfi and return extracted fields.

    Returns:
        {
            "vendor":  str | None,
            "date":    datetime.date | None,
            "amount":  float | None,
            "raw_text": str,          # full Veryfi OCR text (for debugging)
            "line_items": list[dict], # individual items if Veryfi extracts them
            "confidence": {
                "vendor": bool,
                "date":   bool,
                "amount": bool,
            },
            "ocr_available": bool,
        }
    """
    result = {
        "vendor": None,
        "date": None,
        "amount": None,
        "raw_text": "",
        "line_items": [],
        "confidence": {"vendor": False, "date": False, "amount": False},
        "ocr_available": VERYFI_INSTALLED,
    }

    if not VERYFI_INSTALLED:
        return result

    client_id, client_secret, api_key = _get_credentials()
    if not client_id:
        result["ocr_available"] = False
        return result

    try:
        client = VeryfiClient(client_id, client_secret, api_key)

        # Veryfi accepts base64-encoded image bytes
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = client.process_document_from_base64(
            b64,
            file_name=file_name,
            categories=[],  # let Veryfi auto-categorise
        )

        vendor = response.get("vendor", {}).get("name") or response.get("bill_to_name")
        date   = _parse_date(response.get("date"))
        amount = response.get("total")
        if amount is not None:
            amount = round(float(amount), 2)

        line_items = [
            {
                "description": item.get("description", ""),
                "quantity":    item.get("quantity", 1),
                "total":       item.get("total", 0),
            }
            for item in response.get("line_items", [])
        ]

        result.update({
            "vendor":     vendor,
            "date":       date,
            "amount":     amount,
            "raw_text":   response.get("ocr_text", ""),
            "line_items": line_items,
            "confidence": {
                "vendor": bool(vendor),
                "date":   bool(date),
                "amount": bool(amount),
            },
        })

    except Exception:
        # API failure is non-fatal — user fills in form manually
        pass

    return result
