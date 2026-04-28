"""
scripts/seed_leases.py — One-time script to seed active lease records into the Tenants sheet.

Run once from the project root:
    py scripts/seed_leases.py

Each lease gets a single "Move-In" entry with lease dates, rent, and deposit
so the Lease Renewals page can display them immediately.
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

LEASES = [
    {
        "property":         "Tampa",
        "tenant_name":      "Trista Harroun & Josh Harroun",
        "lease_start":      "2025-05-23",
        "lease_end":        "2026-05-31",
        "monthly_rent":     2945.00,
        "security_deposit": 2945.00,
        "entry_type":       "Move-In",
        "entry_date":       "2025-05-23",
        "subject":          "Lease signed — Trista & Josh Harroun",
        "body":             (
            "Lease FL-90910197 signed via Avail. "
            "Tenants: Trista Harroun (tharroun1@yahoo.com, 616-648-7937) and "
            "Josh Harroun (josh.harroun@yahoo.com, 616-446-1225). "
            "Pet deposit: $300. Late fee: $25/day after the 5th. "
            "60-day notice required to vacate."
        ),
        "doc_url": "",
    },
    {
        "property":         "Winter Garden (Regal)",
        "tenant_name":      "Brian Waller & Victoria Peck",
        "lease_start":      "2025-12-01",
        "lease_end":        "2026-05-31",
        "monthly_rent":     2100.00,
        "security_deposit": 1835.00,
        "entry_type":       "Move-In",
        "entry_date":       "2025-12-01",
        "subject":          "Lease signed — Brian Waller & Victoria Peck",
        "body":             (
            "Lease FL-91017181 signed via Avail. "
            "Tenants: Brian Waller (brian9581324@yahoo.com, 305-975-7977) and "
            "Victoria Peck (riamcqueen16@gmail.com, 860-639-8234). "
            "Pet deposit: $300. Utilities included at $240/mo. Pest control $40/mo. "
            "Late fee: $25/day after the 5th. 60-day notice required to vacate."
        ),
        "doc_url": "",
    },
    {
        "property":         "Tampa",
        "tenant_name":      "Trista Harroun & Josh Harroun",
        "lease_start":      "2026-06-01",
        "lease_end":        "2027-05-31",
        "monthly_rent":     3025.00,
        "security_deposit": 2945.00,
        "entry_type":       "Lease Renewal",
        "entry_date":       "2026-06-01",
        "subject":          "Lease renewal — Trista & Josh Harroun",
        "body":             (
            "Lease FL-91114486 renewal signed via Avail. "
            "Term: 2026-06-01 through 2027-05-31. "
            "Rent increased to $3,025/mo. Security deposit: $2,945. "
            "Tenants: Trista Harroun (tharroun1@yahoo.com, 616-648-7937) and "
            "Josh Harroun (josh.harroun@yahoo.com, 616-446-1225). "
            "Pet deposit: $300. Late fee: $25/day after the 5th. "
            "60-day notice required to vacate."
        ),
        "doc_url": "",
    },
    {
        "property":         "Winter Garden (Regal)",
        "tenant_name":      "Brian Waller & Victoria Peck",
        "lease_start":      "2026-06-01",
        "lease_end":        "2026-11-30",
        "monthly_rent":     2100.00,
        "security_deposit": 1835.00,
        "entry_type":       "Lease Renewal",
        "entry_date":       "2026-06-01",
        "subject":          "Lease renewal — Brian Waller & Victoria Peck",
        "body":             (
            "Lease FL-91114492 renewal signed via Avail. "
            "Term: 2026-06-01 through 2026-11-30 (6-month term). "
            "Rent unchanged at $2,100/mo. Security deposit: $1,835. "
            "Tenants: Brian Waller (brian9581324@yahoo.com, 305-975-7977) and "
            "Victoria Peck (riamcqueen16@gmail.com, 860-639-8234). "
            "Pet deposit: $300. Utilities included at $240/mo. Pest control $40/mo. "
            "Late fee: $25/day after the 5th. 60-day notice required to vacate."
        ),
        "doc_url": "",
    },
    {
        "property":         "Winter Garden (Charlotte)",
        "tenant_name":      "",
        "lease_start":      "2025-05-01",
        "lease_end":        "",
        "monthly_rent":     3300.00,
        "security_deposit": 2235.00,
        "entry_type":       "Move-In",
        "entry_date":       "2025-05-01",
        "subject":          "Lease signed — 110 Charlotte St (month-to-month)",
        "body":             (
            "Lease FL-90902799 created via Avail. "
            "110 Charlotte St, Winter Garden, FL 34787. "
            "Month-to-month tenancy starting 2025-05-01. "
            "No lessees listed on lease at time of signing. "
            "Rent: $3,300/mo. Security deposit: $2,235. Pet deposit: $300. "
            "Late fee: $25/day after 5th. 30-day written notice to terminate."
        ),
        "doc_url": "",
    },
    {
        "property":         "Palm Harbor",
        "tenant_name":      "Kyle Vibbert",
        "lease_start":      "2025-11-01",
        "lease_end":        "2026-10-31",
        "monthly_rent":     2420.00,
        "security_deposit": 2335.00,
        "entry_type":       "Move-In",
        "entry_date":       "2025-11-01",
        "subject":          "Lease signed — Kyle Vibbert",
        "body":             (
            "Lease FL-90969673 signed via Avail. "
            "Tenant: Kyle Vibbert (globalshine701@gmail.com, 863-808-3125). "
            "Pet deposit: $600. Late fee: $25/day after the 5th. "
            "60-day notice required to vacate."
        ),
        "doc_url": "",
    },
]


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
    ws = client.open_by_key(spreadsheet_id).worksheet("Tenants")

    now = datetime.datetime.now().isoformat(timespec="seconds")

    for lease in LEASES:
        row = [
            now,
            lease["property"],
            lease["tenant_name"],
            lease["lease_start"],
            lease["lease_end"],
            lease["monthly_rent"],
            lease["security_deposit"],
            lease["entry_type"],
            lease["entry_date"],
            lease["subject"],
            lease["body"],
            lease["doc_url"],
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"[OK] Added lease for {lease['property']} — {lease['tenant_name']}")

    print("\nDone. Refresh the Lease Renewals page in the app.")


if __name__ == "__main__":
    main()
