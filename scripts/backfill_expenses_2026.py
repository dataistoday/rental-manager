"""
scripts/backfill_expenses_2026.py — Backfill 2026 expenses from manual Schedule E tracking.

Sources: Schedule E 2026.pdf — Jan/Feb 2026 entries manually tracked by owner.
         Adds all line items with amounts, plus recurring items through April 2026.

NOTE: All amounts are already at their deductible value (80% rule or 50% rule applied
      where noted). March/April utilities (Duke, Metro Net, WG Water) are NOT included
      here — those vary per bill. Add them manually or let gmail_poller handle them.

Copy to main scripts/ folder first, then run:
    copy ".claude\worktrees\elastic-banzai-b83b5e\scripts\backfill_expenses_2026.py" "scripts\backfill_expenses_2026.py"
    py scripts/backfill_expenses_2026.py
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

EXPENSES = [
    # ── Repairs ──────────────────────────────────────────────────────────────
    {
        "date": "2026-02-04", "property": "Palm Harbor",
        "vendor": "Bella Plumbing", "amount": 450.00,
        "category": "Repairs", "description": "Tub drain cleared",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-02-15", "property": "Palm Harbor",
        "vendor": "Bella Plumbing", "amount": 1650.00,
        "category": "Repairs", "description": "Shut off valve and tub leak fix",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-02-13", "property": "Palm Harbor",
        "vendor": "Home Depot", "amount": 692.29,
        "category": "Repairs", "description": "Vanity and faucets",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-02-14", "property": "Palm Harbor",
        "vendor": "Lowes", "amount": 41.55,
        "category": "Repairs", "description": "Vanity install pieces",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },

    # ── Cleaning & Maintenance ───────────────────────────────────────────────
    {
        "date": "2026-02-15", "property": "Palm Harbor",
        "vendor": "First American Home Warranty", "amount": 510.00,
        "category": "Cleaning and Maintenance", "description": "Home warranty",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-01-12", "property": "Winter Garden (Regal)",
        "vendor": "Rowland Pest Control", "amount": 24.50,
        "category": "Cleaning and Maintenance", "description": "Pest control — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$49",
    },
    {
        "date": "2026-02-12", "property": "Winter Garden (Regal)",
        "vendor": "Rowland Pest Control", "amount": 24.50,
        "category": "Cleaning and Maintenance", "description": "Pest control — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$49",
    },
    {
        "date": "2026-03-12", "property": "Winter Garden (Regal)",
        "vendor": "Rowland Pest Control", "amount": 24.50,
        "category": "Cleaning and Maintenance", "description": "Pest control — 50% share (estimated)",
        "payment_method": "", "notes": "Estimated based on Jan/Feb recurring amount; verify",
    },
    {
        "date": "2026-04-12", "property": "Winter Garden (Regal)",
        "vendor": "Rowland Pest Control", "amount": 24.50,
        "category": "Cleaning and Maintenance", "description": "Pest control — 50% share (estimated)",
        "payment_method": "", "notes": "Estimated based on Jan/Feb recurring amount; verify",
    },
    {
        "date": "2026-01-06", "property": "Winter Garden (Regal)",
        "vendor": "Blackwells Cleanup Services", "amount": 20.00,
        "category": "Cleaning and Maintenance", "description": "Cleanup service",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-02-03", "property": "Winter Garden (Regal)",
        "vendor": "Blackwells Cleanup Services", "amount": 20.00,
        "category": "Cleaning and Maintenance", "description": "Cleanup service",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-03-03", "property": "Winter Garden (Regal)",
        "vendor": "Blackwells Cleanup Services", "amount": 20.00,
        "category": "Cleaning and Maintenance", "description": "Cleanup service (estimated)",
        "payment_method": "", "notes": "Estimated based on Jan/Feb recurring amount; verify",
    },
    {
        "date": "2026-04-03", "property": "Winter Garden (Regal)",
        "vendor": "Blackwells Cleanup Services", "amount": 20.00,
        "category": "Cleaning and Maintenance", "description": "Cleanup service (estimated)",
        "payment_method": "", "notes": "Estimated based on Jan/Feb recurring amount; verify",
    },
    {
        "date": "2026-02-07", "property": "Winter Garden (Regal)",
        "vendor": "Field Perfection LLC", "amount": 60.00,
        "category": "Cleaning and Maintenance", "description": "Gutter cleaning",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },

    # ── Supplies ─────────────────────────────────────────────────────────────
    {
        "date": "2026-02-13", "property": "Palm Harbor",
        "vendor": "Harbor Freight", "amount": 21.49,
        "category": "Supplies", "description": "80x144 XL moving blanket",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-02-08", "property": "Palm Harbor",
        "vendor": "Home Depot", "amount": 47.07,
        "category": "Supplies", "description": "Blink cameras",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-02-06", "property": "Palm Harbor",
        "vendor": "Ace Hardware", "amount": 115.93,
        "category": "Supplies", "description": "Keys and lock",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    # Regal tools — amounts already reflect 80% deduction as entered in Schedule E
    {
        "date": "2026-01-22", "property": "Winter Garden (Regal)",
        "vendor": "Ace Hardware", "amount": 132.02,
        "category": "Supplies", "description": "Tools — screwdriver, adaptors",
        "payment_method": "", "notes": "Backfilled; 80% deduction already applied (full ~$165.02)",
    },
    {
        "date": "2026-01-21", "property": "Winter Garden (Regal)",
        "vendor": "Harbor Freight", "amount": 140.55,
        "category": "Supplies", "description": "Drill",
        "payment_method": "", "notes": "Backfilled; 80% deduction already applied (full ~$175.69)",
    },
    {
        "date": "2026-01-21", "property": "Winter Garden (Regal)",
        "vendor": "AutoZone", "amount": 23.85,
        "category": "Supplies", "description": "Wrench extender",
        "payment_method": "", "notes": "Backfilled; 80% deduction already applied (full ~$29.81)",
    },
    {
        "date": "2026-01-21", "property": "Winter Garden (Regal)",
        "vendor": "Home Depot", "amount": 281.62,
        "category": "Supplies", "description": "Impact wrench",
        "payment_method": "", "notes": "Backfilled; 80% deduction already applied (full ~$352.03)",
    },

    # ── Auto & Travel (lodging while working on properties) ──────────────────
    {
        "date": "2026-02-07", "property": "Palm Harbor",
        "vendor": "Silver Dollar Camp Ground", "amount": 203.00,
        "category": "Auto and Travel", "description": "Camping night during W Canal work trip",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },
    {
        "date": "2026-01-24", "property": "Tampa",
        "vendor": "Silver Dollar Camp Ground", "amount": 40.00,
        "category": "Auto and Travel", "description": "Camp ground — Elmwood trip",
        "payment_method": "", "notes": "Backfilled from Schedule E",
    },

    # ── Utilities (50% already applied per 50% rule) ─────────────────────────
    # NOTE: March/April utilities NOT included — amounts vary per bill.
    # Add manually or via gmail_poller once bills are received.
    {
        "date": "2026-01-06", "property": "Winter Garden (Regal)",
        "vendor": "Duke Energy", "amount": 170.41,
        "category": "Utilities", "description": "Electricity — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$340.81",
    },
    {
        "date": "2026-02-15", "property": "Winter Garden (Regal)",
        "vendor": "Duke Energy", "amount": 186.96,
        "category": "Utilities", "description": "Electricity — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$373.91",
    },
    {
        "date": "2026-01-06", "property": "Winter Garden (Regal)",
        "vendor": "Winter Garden Utilities", "amount": 39.77,
        "category": "Utilities", "description": "Water — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$79.54",
    },
    {
        "date": "2026-02-05", "property": "Winter Garden (Regal)",
        "vendor": "Winter Garden Utilities", "amount": 46.94,
        "category": "Utilities", "description": "Water — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$93.87",
    },
    {
        "date": "2026-01-31", "property": "Winter Garden (Regal)",
        "vendor": "Metro Net", "amount": 31.88,
        "category": "Utilities", "description": "Internet — 50% share",
        "payment_method": "", "notes": "Backfilled from Schedule E; full bill ~$63.75",
    },

    # ── Management Fees — Avail Jan–Apr 2026 ($9/property/month, split 4 ways) ─
    # Jan
    {"date": "2026-01-22", "property": "Palm Harbor", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    {"date": "2026-01-22", "property": "Winter Garden (Charlotte)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    {"date": "2026-01-22", "property": "Tampa", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    {"date": "2026-01-22", "property": "Winter Garden (Regal)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    # Feb
    {"date": "2026-02-22", "property": "Palm Harbor", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    {"date": "2026-02-22", "property": "Winter Garden (Charlotte)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    {"date": "2026-02-22", "property": "Tampa", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    {"date": "2026-02-22", "property": "Winter Garden (Regal)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Backfilled from Schedule E"},
    # Mar
    {"date": "2026-03-22", "property": "Palm Harbor", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    {"date": "2026-03-22", "property": "Winter Garden (Charlotte)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    {"date": "2026-03-22", "property": "Tampa", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    {"date": "2026-03-22", "property": "Winter Garden (Regal)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    # Apr
    {"date": "2026-04-22", "property": "Palm Harbor", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    {"date": "2026-04-22", "property": "Winter Garden (Charlotte)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    {"date": "2026-04-22", "property": "Tampa", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
    {"date": "2026-04-22", "property": "Winter Garden (Regal)", "vendor": "Avail", "amount": 9.00,
     "category": "Management Fees", "description": "Property mgmt software — 1/4 share", "payment_method": "", "notes": "Recurring — verify charge occurred"},
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
    ws = client.open_by_key(spreadsheet_id).worksheet("Expenses")

    now = datetime.datetime.now().isoformat(timespec="seconds")

    for e in EXPENSES:
        row = [
            now,
            e["property"],
            e["date"],
            e["vendor"],
            round(e["amount"], 2),
            e["category"],
            e["description"],
            "",   # receipt_url
            e["payment_method"],
            e["notes"],
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"[OK] {e['date']} | {e['property']:<28} | {e['vendor']:<30} | ${e['amount']:.2f}")

    print(f"\nDone. {len(EXPENSES)} rows written.")
    print("\nSTILL NEEDED (amounts vary — add manually or via gmail_poller):")
    print("  • Duke Energy Mar/Apr — Winter Garden (Regal), 50% share")
    print("  • Winter Garden Utilities Mar/Apr — Winter Garden (Regal), 50% share")
    print("  • Metro Net Feb/Mar/Apr — Winter Garden (Regal), 50% share")
    print("  • Charlotte First American Home Warranty — amount not visible in PDF")
    print("  • Extra Space Storage 2/14 — Palm Harbor, amount not visible in PDF")


if __name__ == "__main__":
    main()
