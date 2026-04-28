"""
scripts/backfill_rent.py — One-time script to backfill assumed rent payments.

Assumptions:
  - Tampa: Trista & Josh Harroun, $2,945/mo, May 2025–Apr 2026
  - Winter Garden (Regal): Brian Waller & Victoria Peck, $2,100/mo, Dec 2025–Apr 2026
  - Winter Garden (Charlotte): unknown tenant, $3,300/mo, May 2025–Apr 2026
  - Palm Harbor: skipped (eviction situation — fill manually)

All payments assumed received on the 1st of each month.
Run once, then verify in the Rent Income sheet and delete any that don't apply.

Copy to main scripts/ folder first, then run:
    copy ".claude\worktrees\elastic-banzai-b83b5e\scripts\backfill_rent.py" "scripts\backfill_rent.py"
    py scripts/backfill_rent.py
"""

import datetime
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import gspread
from google.oauth2.service_account import Credentials as ServiceCredentials

CREDENTIALS_FILE = PROJECT_ROOT / os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def months_range(start_year, start_month, end_year, end_month):
    """Yield (year, month) tuples inclusive."""
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


PAYMENTS = []

# Tampa — Trista & Josh Harroun, $2,945/mo, May 2025–Apr 2026
for y, m in months_range(2025, 5, 2026, 4):
    PAYMENTS.append({
        "property":       "Tampa",
        "tenant_name":    "Trista Harroun & Josh Harroun",
        "date_received":  f"{y}-{m:02d}-01",
        "amount":         2945.00,
        "late_fee":       0.0,
        "period_start":   f"{y}-{m:02d}-01",
        "period_end":     (datetime.date(y, m, 1).replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1),
        "payment_method": "",
        "notes":          "Backfilled — verify and correct as needed",
    })

# Winter Garden (Regal) — Brian Waller & Victoria Peck, $2,100/mo, Dec 2025–Apr 2026
for y, m in months_range(2025, 12, 2026, 4):
    PAYMENTS.append({
        "property":       "Winter Garden (Regal)",
        "tenant_name":    "Brian Waller & Victoria Peck",
        "date_received":  f"{y}-{m:02d}-01",
        "amount":         2100.00,
        "late_fee":       0.0,
        "period_start":   f"{y}-{m:02d}-01",
        "period_end":     (datetime.date(y, m, 1).replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1),
        "payment_method": "",
        "notes":          "Backfilled — verify and correct as needed",
    })

# Winter Garden (Charlotte) — tenant unknown, $3,300/mo, May 2025–Apr 2026
for y, m in months_range(2025, 5, 2026, 4):
    PAYMENTS.append({
        "property":       "Winter Garden (Charlotte)",
        "tenant_name":    "",
        "date_received":  f"{y}-{m:02d}-01",
        "amount":         3300.00,
        "late_fee":       0.0,
        "period_start":   f"{y}-{m:02d}-01",
        "period_end":     (datetime.date(y, m, 1).replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1),
        "payment_method": "",
        "notes":          "Backfilled — verify and correct as needed. Tenant name unknown.",
    })

# Palm Harbor — Kyle Vibbert, $2,420/mo, Jan + Feb 2026 only (confirmed paid)
for y, m in [(2026, 1), (2026, 2)]:
    PAYMENTS.append({
        "property":       "Palm Harbor",
        "tenant_name":    "Kyle Vibbert",
        "date_received":  f"{y}-{m:02d}-01",
        "amount":         2420.00,
        "late_fee":       0.0,
        "period_start":   f"{y}-{m:02d}-01",
        "period_end":     (datetime.date(y, m, 1).replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1),
        "payment_method": "",
        "notes":          "Backfilled — confirmed paid",
    })


def main():
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "")
    if not spreadsheet_id or spreadsheet_id == "REPLACE_WITH_SPREADSHEET_ID":
        print("[ERROR] SPREADSHEET_ID not set in .env")
        sys.exit(1)

    if not CREDENTIALS_FILE.exists():
        print(f"[ERROR] credentials.json not found at {CREDENTIALS_FILE}")
        sys.exit(1)

    creds = ServiceCredentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(spreadsheet_id).worksheet("Rent Income")

    now = datetime.datetime.now().isoformat(timespec="seconds")

    for p in PAYMENTS:
        period_end = p["period_end"]
        if isinstance(period_end, datetime.date):
            period_end = period_end.isoformat()

        row = [
            now,
            p["property"],
            p["tenant_name"],
            p["date_received"],
            p["amount"],
            p["late_fee"],
            p["period_start"],
            period_end,
            p["payment_method"],
            p["notes"],
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"[OK] {p['property']} — {p['date_received']} — ${p['amount']:,.2f}")

    print(f"\nDone. {len(PAYMENTS)} rows written. Review in the Rent Income sheet.")


if __name__ == "__main__":
    main()
