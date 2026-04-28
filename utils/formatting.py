"""utils/formatting.py — Display formatters used across all pages."""

import re
import datetime
from typing import Optional


def format_currency(value) -> str:
    """Format a number as USD currency string. Returns '' for blank/None."""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return ""


def format_phone(phone: str) -> str:
    """Format a 10-digit string as (555) 867-5309. Pass-through if not 10 digits."""
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return str(phone) if phone else ""


def format_date(value) -> str:
    """
    Format a date or date-string as MM/DD/YYYY.
    Accepts datetime.date, ISO strings (YYYY-MM-DD), or US strings (MM/DD/YYYY).
    Returns '' for blank/None.
    """
    if not value:
        return ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%m/%d/%Y")
    s = str(value).strip()
    # Already MM/DD/YYYY
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
        return s
    # ISO format YYYY-MM-DD
    try:
        d = datetime.date.fromisoformat(s)
        return d.strftime("%m/%d/%Y")
    except ValueError:
        return s


def format_miles(value) -> str:
    """Format a mileage number with one decimal place."""
    try:
        return f"{float(value):,.1f} mi"
    except (TypeError, ValueError):
        return ""


def status_badge(status: str) -> str:
    """Return a coloured emoji prefix for a maintenance status."""
    badges = {
        "Open":        "🔴 Open",
        "In Progress": "🟡 In Progress",
        "Resolved":    "🟢 Resolved",
    }
    return badges.get(status, status)


def priority_badge(priority: str) -> str:
    """Return a coloured emoji prefix for a maintenance priority."""
    badges = {
        "Low":       "🔵 Low",
        "Medium":    "🟡 Medium",
        "High":      "🟠 High",
        "Emergency": "🔴 Emergency",
    }
    return badges.get(priority, priority)
