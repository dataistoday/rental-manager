"""
scripts/gmail_poller.py — Gmail Receipt Auto-Importer
======================================================

Scans Gmail for emails labeled "rental-receipts", extracts vendor/date/amount
via Veryfi OCR (with an HTML-body fallback), and appends a row to the Expenses
Google Sheet automatically.

─────────────────────────────────────────────────────────────────────────────
FIRST-TIME SETUP  (do this once)
─────────────────────────────────────────────────────────────────────────────
1. In Google Cloud Console (same project you already have):
     APIs & Services → Enable APIs → search "Gmail API" → Enable

2. APIs & Services → Credentials → + Create Credentials → OAuth 2.0 Client ID
     Application type: Desktop app
     Name: Gmail Poller (anything)
     → Download JSON → save as  gmail_oauth_client.json  in the project root

3. Run the auth setup (opens a browser tab once):
     python scripts/gmail_poller.py --setup

4. In Gmail, create a label called  rental-receipts
     (Settings → Labels → Create new label)

5. Test it:
     python scripts/gmail_poller.py --dry-run

6. Schedule with Windows Task Scheduler to run every 5 minutes:
     Program: C:\\path\\to\\.venv\\Scripts\\python.exe
     Arguments: scripts\\gmail_poller.py
     Start in: C:\\path\\to\\rental-manager  (project root)

─────────────────────────────────────────────────────────────────────────────
HOW TO USE (day-to-day)
─────────────────────────────────────────────────────────────────────────────
Forward any receipt email to yourself, then apply the "rental-receipts" label.
Or set up a Gmail filter to auto-label emails from stores you use (Home Depot,
Lowe's, Amazon, etc.).

The script processes each labeled email and moves it to "rental-receipts-done".

─────────────────────────────────────────────────────────────────────────────
SUBJECT LINE SHORTCUTS  (optional — to set property and flags)
─────────────────────────────────────────────────────────────────────────────
Include a property code anywhere in the subject (case-insensitive):
  PH  or  palm harbor        → Palm Harbor        (DEFAULT if nothing found)
  TPA or  tampa              → Tampa
  WGR or  regal              → Winter Garden (Regal)
  WGC or  charlotte          → Winter Garden (Charlotte)

Include TOOLS anywhere in the subject to apply the 80% deduction rule:
  "PH TOOLS Home Depot"  → Palm Harbor, saves 80% of receipt total

Examples:
  Forward with subject:  "PH Home Depot supplies"
  Forward with subject:  "TPA TOOLS harbor freight"
  Forward unchanged:     "Your Home Depot receipt" → defaults to Palm Harbor

─────────────────────────────────────────────────────────────────────────────
COMMAND-LINE FLAGS
─────────────────────────────────────────────────────────────────────────────
  --setup      Run OAuth flow (first time only)
  --dry-run    Parse emails but do NOT write to Sheets or move labels
  --verbose    Print detailed info for every email processed
"""

import argparse
import base64
import datetime
import os
import re
import sys
from pathlib import Path

# ── Make project-root importable so we can reuse ocr/receipt_parser.py ──────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ── Google / Gmail imports ───────────────────────────────────────────────────
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials as ServiceCredentials
import gspread

# ── Veryfi OCR (reuse existing receipt_parser) ───────────────────────────────
# receipt_parser falls back to os.getenv when st.secrets isn't available
from ocr.receipt_parser import parse_receipt

# ── Config ───────────────────────────────────────────────────────────────────
from config import PROPERTIES, IRS_SCHEDULE_E_CATEGORIES, SHEET_TABS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# File paths (project root)
OAUTH_CLIENT_FILE = PROJECT_ROOT / "gmail_oauth_client.json"
TOKEN_FILE        = PROJECT_ROOT / "gmail_token.json"
CREDENTIALS_FILE  = PROJECT_ROOT / os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# Gmail label names
LABEL_INBOX    = os.getenv("GMAIL_LABEL_NAME", "rental-receipts")
LABEL_DONE     = os.getenv("GMAIL_LABEL_DONE", "rental-receipts-done")

# Default values when subject gives no hint
DEFAULT_PROPERTY = "Palm Harbor"
DEFAULT_CATEGORY = "Supplies"

# Property keyword → PROPERTIES list value
PROPERTY_ALIASES: dict[str, str] = {
    "ph":              "Palm Harbor",
    "palm harbor":     "Palm Harbor",
    "palmharbor":      "Palm Harbor",
    "254 w canal":     "Palm Harbor",
    "canal dr":        "Palm Harbor",
    "tpa":             "Tampa",
    "tampa":           "Tampa",
    "8723 elmwood":    "Tampa",
    "elmwood":         "Tampa",
    "wgr":             "Winter Garden (Regal)",
    "regal":           "Winter Garden (Regal)",
    "13 regal":        "Winter Garden (Regal)",
    "wgc":             "Winter Garden (Charlotte)",
    "charlotte":       "Winter Garden (Charlotte)",
}

# Attachment MIME types we'll send to Veryfi
OCR_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}

# Regexes to pull a dollar total from plain-text/HTML email bodies (fallback).
# Ordered most-specific → least-specific so we don't grab a subtotal by accident.
AMOUNT_PATTERNS = [
    r"order\s+total[:\s]*\$?([\d,]+\.\d{2})",
    r"grand\s+total[:\s]*\$?([\d,]+\.\d{2})",
    r"total\s+applied\s+amount[:\s]*\$?([\d,]+\.\d{2})",   # Rowland Pest style
    r"transaction\s+amount[:\s]*\$?([\d,]+\.\d{2})",        # Rowland Pest style
    r"current\s+amount\s+paid[:\s]*\$?([\d,]+\.\d{2})",     # Rowland Pest style
    r"total\s+charged[:\s]*\$?([\d,]+\.\d{2})",
    r"amount\s+charged[:\s]*\$?([\d,]+\.\d{2})",
    r"total\s+due[:\s]*\$?([\d,]+\.\d{2})",
    r"service\s+total[:\s]*\$?([\d,]+\.\d{2})",             # Rowland Pest style
    r"\btotal[:\s]+\$?([\d,]+\.\d{2})",
]

# Regexes to extract a date from the email body (fallback when no OCR attachment).
# Each tuple is (pattern, date-parse-format).
DATE_PATTERNS = [
    # "Transaction Date: 4/13/26 8:01am EDT"  or  "4/13/2026"
    (r"transaction\s+date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})", "%m/%d/%y"),
    (r"transaction\s+date[:\s]+(\d{1,2}/\d{1,2}/\d{4})",   "%m/%d/%Y"),
    # "Date: April 13, 2026" or "April 13, 26"
    (r"(\w+ \d{1,2},\s*\d{4})",                              "%B %d, %Y"),
    # ISO  2026-04-13
    (r"(\d{4}-\d{2}-\d{2})",                                 "%Y-%m-%d"),
    # MM/DD/YY  or  MM/DD/YYYY
    (r"(\d{1,2}/\d{1,2}/\d{4})",                             "%m/%d/%Y"),
    (r"(\d{1,2}/\d{1,2}/\d{2})",                             "%m/%d/%y"),
]

# Recurring Winter Garden (Regal) senders: always map to Regal + 50% deduction.
# Matched case-insensitively against the From: header AND subject line (handles forwards).
# Key = substring to look for; value = (vendor name, Schedule E category).
UTILITY_50_SENDERS: dict[str, tuple[str, str]] = {
    "duke-energy":              ("Duke Energy",             "Utilities"),
    "duke energy":              ("Duke Energy",             "Utilities"),
    "metronet":                 ("Metro Net",               "Utilities"),
    "metro net":                ("Metro Net",               "Utilities"),
    "cityofwintergarden":       ("Winter Garden Utilities", "Utilities"),
    "winter garden utilities":  ("Winter Garden Utilities", "Utilities"),
    "cwgdn":                    ("Winter Garden Utilities", "Utilities"),
    "rowland pest":             ("Rowland Pest Control",    "Cleaning and Maintenance"),
    "rowlandpest":              ("Rowland Pest Control",    "Cleaning and Maintenance"),
}

# Senders whose charge should be split evenly across ALL properties (portfolio-wide
# services like rental management software). Writes one expense row per property,
# each at amount/len(PROPERTIES). Matched against From: header AND subject line.
# Key = substring; value = (vendor, Schedule E category).
SPLIT_SENDERS: dict[str, tuple[str, str]] = {
    "avail.co":  ("Avail", "Management Fees"),
    "avail ":    ("Avail", "Management Fees"),
}


# Body-text hints that indicate a specific property (scans the email body, not just subject).
# Checked only when the subject contains no property code.
# Keys are lowercase substrings to look for; values map to PROPERTIES entries.
BODY_PROPERTY_HINTS: dict[str, str] = {
    # Address-based (most specific — check these first)
    "8723 elmwood":  "Tampa",
    "elmwood lane":  "Tampa",
    "254 w canal":   "Palm Harbor",
    "w canal dr":    "Palm Harbor",
    "canal dr":      "Palm Harbor",
    "13 regal":      "Winter Garden (Regal)",
    # Name/keyword fallbacks
    "regal":         "Winter Garden (Regal)",
    "charlotte":     "Winter Garden (Charlotte)",
    "palm harbor":   "Palm Harbor",
    "tampa":         "Tampa",
}


# ---------------------------------------------------------------------------
# Gmail OAuth helpers
# ---------------------------------------------------------------------------

def get_gmail_service():
    """Return an authorised Gmail API service, refreshing / re-authorising as needed."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not OAUTH_CLIENT_FILE.exists():
                sys.exit(
                    f"\n[ERROR] gmail_oauth_client.json not found at {OAUTH_CLIENT_FILE}\n"
                    "Follow step 2 in the setup instructions at the top of this file.\n"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(OAUTH_CLIENT_FILE), GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print(f"[AUTH] Gmail token saved to {TOKEN_FILE}")

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Gmail label helpers
# ---------------------------------------------------------------------------

def get_or_create_label(service, name: str) -> str:
    """Return the label ID for *name*, creating the label in Gmail if needed."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"].lower() == name.lower():
            return lbl["id"]

    # Create it
    new_label = service.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
    ).execute()
    print(f"[SETUP] Created Gmail label: '{name}'")
    return new_label["id"]


def list_unprocessed_messages(service, label_id: str) -> list[dict]:
    """Return all messages that carry *label_id*."""
    results = service.users().messages().list(
        userId="me", labelIds=[label_id], maxResults=50
    ).execute()
    return results.get("messages", [])


def get_message(service, msg_id: str) -> dict:
    return service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()


def move_to_done(service, msg_id: str, label_inbox_id: str, label_done_id: str, dry_run: bool):
    """Remove 'rental-receipts' label, add 'rental-receipts-done', mark as read."""
    if dry_run:
        print("  [DRY-RUN] Would move message to rental-receipts-done")
        return
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={
            "addLabelIds":    [label_done_id],
            "removeLabelIds": [label_inbox_id, "UNREAD"],
        },
    ).execute()


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------

def decode_part(data: str) -> bytes:
    """Base64url-decode a Gmail message part."""
    return base64.urlsafe_b64decode(data + "==")


def get_subject(message: dict) -> str:
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "subject":
            return h["value"]
    return ""


def get_sender(message: dict) -> str:
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "from":
            return h["value"]
    return ""


def parse_property_from_subject(subject: str) -> str:
    """Return the matching PROPERTIES entry from subject keywords, or DEFAULT_PROPERTY."""
    s = subject.lower()
    for alias, prop in PROPERTY_ALIASES.items():
        if alias in s:
            return prop
    return DEFAULT_PROPERTY


def is_tools_purchase(subject: str) -> bool:
    return "tools" in subject.lower() or "tool" in subject.lower()


def match_utility_sender(sender: str, subject: str) -> tuple[str, str] | None:
    """
    Return (vendor_name, schedule_e_category) if this email is from one of the
    recurring Winter Garden (Regal) senders subject to the 50% deduction rule.
    Matches sender AND subject so forwarded bills still trigger the rule.
    """
    haystack = f"{sender} {subject}".lower()
    for keyword, (vendor, category) in UTILITY_50_SENDERS.items():
        if keyword in haystack:
            return vendor, category
    return None


def match_split_sender(sender: str, subject: str) -> tuple[str, str] | None:
    """
    Return (vendor_name, schedule_e_category) if this email is from a sender
    whose charge should be split evenly across ALL properties.
    """
    haystack = f"{sender} {subject}".lower()
    for keyword, (vendor, category) in SPLIT_SENDERS.items():
        if keyword in haystack:
            return vendor, category
    return None


def extract_attachments(service, message: dict) -> list[tuple[bytes, str, str]]:
    """
    Return list of (file_bytes, filename, mime_type) for all OCR-able attachments.
    Handles both inline data and attachment IDs.
    """
    attachments = []
    msg_id = message["id"]

    def walk_parts(parts):
        for part in parts:
            mime = part.get("mimeType", "")
            filename = part.get("filename", "")
            body = part.get("body", {})

            if mime in OCR_MIME_TYPES:
                if body.get("data"):
                    attachments.append((decode_part(body["data"]), filename or "receipt.jpg", mime))
                elif body.get("attachmentId"):
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=msg_id, id=body["attachmentId"]
                    ).execute()
                    attachments.append((decode_part(att["data"]), filename or "receipt.jpg", mime))

            # Recurse into multipart
            if "parts" in part:
                walk_parts(part["parts"])

    payload = message.get("payload", {})
    if "parts" in payload:
        walk_parts(payload["parts"])
    elif payload.get("mimeType", "") in OCR_MIME_TYPES:
        body = payload.get("body", {})
        if body.get("data"):
            attachments.append((decode_part(body["data"]), "receipt.jpg", payload["mimeType"]))

    return attachments


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace so regex can match across table cells."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_body_text(message: dict) -> str:
    """
    Return body as a single cleaned string for regex parsing.
    Prefers plain-text part; falls back to HTML with tags stripped.
    """
    plain_parts = []
    html_parts  = []

    def walk_parts(parts):
        for part in parts:
            mime = part.get("mimeType", "")
            body = part.get("body", {})
            if body.get("data"):
                raw = decode_part(body["data"]).decode("utf-8", errors="ignore")
                if mime == "text/plain":
                    plain_parts.append(raw)
                elif mime == "text/html":
                    html_parts.append(_strip_html(raw))
            if "parts" in part:
                walk_parts(part["parts"])

    payload = message.get("payload", {})
    if "parts" in payload:
        walk_parts(payload["parts"])
    elif payload.get("body", {}).get("data"):
        raw = decode_part(payload["body"]["data"]).decode("utf-8", errors="ignore")
        plain_parts.append(raw)

    # Plain text is already clean; prefer it. Fall back to stripped HTML.
    return " ".join(plain_parts) if plain_parts else " ".join(html_parts)


def parse_amount_from_body(body_text: str) -> float | None:
    """
    Try labeled patterns first (most accurate), then fall back to frequency analysis:
    find all dollar amounts in the email and return the most common non-zero one.
    In a typical receipt email the total appears several times; $0.00 or tax noise
    appears less often, so the mode is usually the correct total.
    """
    # Pass 1 — labeled patterns
    for pattern in AMOUNT_PATTERNS:
        m = re.search(pattern, body_text, re.IGNORECASE)
        if m:
            try:
                return round(float(m.group(1).replace(",", "")), 2)
            except ValueError:
                continue

    # Pass 2 — frequency fallback
    all_amounts = re.findall(r"\$\s*([\d,]+\.\d{2})", body_text)
    if not all_amounts:
        # Also try without the $ sign (some emails omit it in the raw text)
        all_amounts = re.findall(r"\b([\d,]+\.\d{2})\b", body_text)

    if all_amounts:
        from collections import Counter
        counts = Counter(all_amounts)
        # Remove zero-value noise
        counts = {k: v for k, v in counts.items() if float(k.replace(",", "")) > 0}
        if counts:
            best = max(counts, key=lambda k: (counts[k], float(k.replace(",", ""))))
            return round(float(best.replace(",", "")), 2)

    return None


def parse_date_from_body(body_text: str) -> datetime.date | None:
    """Try to extract a transaction date from the email body text."""
    for pattern, fmt in DATE_PATTERNS:
        m = re.search(pattern, body_text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            try:
                # Handle 2-digit years: 26 → 2026
                parsed = datetime.datetime.strptime(raw, fmt).date()
                # Sanity check: reject obviously wrong years
                if 2020 <= parsed.year <= 2040:
                    return parsed
            except ValueError:
                continue
    return None


def parse_property_from_body(body_text: str) -> str | None:
    """
    Scan the email body for property address hints.
    Returns a PROPERTIES value, or None if nothing recognized.
    """
    lower = body_text.lower()
    for hint, prop in BODY_PROPERTY_HINTS.items():
        if hint in lower:
            return prop
    return None


def vendor_from_sender(sender: str) -> str:
    """
    Best-effort vendor name from the From: header.
    'Home Depot <receipts@homedepot.com>' → 'Home Depot'
    'receipts@lowes.com' → 'Lowes'
    """
    # Try display name first
    m = re.match(r'^"?([^"<]+)"?\s*<', sender)
    if m:
        return m.group(1).strip()

    # Fall back to domain name
    m = re.search(r"@([\w.-]+)", sender)
    if m:
        domain = m.group(1).lower()
        # Strip TLD and common prefixes
        parts = domain.split(".")
        name = parts[-2] if len(parts) >= 2 else parts[0]
        return name.replace("-", " ").title()

    return sender.strip()


# ---------------------------------------------------------------------------
# Google Sheets writer (standalone — no Streamlit dependency)
# ---------------------------------------------------------------------------

def _get_sheets_client() -> gspread.Client:
    """Return an authorised gspread client using the service account credentials."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceCredentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=scopes)
    return gspread.authorize(creds)


def write_expense_row(
    property_name: str,
    date: datetime.date,
    vendor: str,
    amount: float,
    category: str,
    description: str,
    notes: str,
    dry_run: bool,
) -> None:
    """Append one row to the Expenses sheet."""
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "")
    if not spreadsheet_id or spreadsheet_id == "REPLACE_WITH_SPREADSHEET_ID":
        print("[ERROR] SPREADSHEET_ID not set in .env — cannot write to Sheets.")
        return

    row = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        property_name,
        date.isoformat(),
        vendor,
        round(amount, 2),
        category,
        description,
        "",        # receipt_url — not uploading to Drive from here
        "",        # payment_method
        notes,
    ]

    if dry_run:
        print(f"  [DRY-RUN] Would write: {row}")
        return

    client = _get_sheets_client()
    tab_name = SHEET_TABS["expenses"]
    ws = client.open_by_key(spreadsheet_id).worksheet(tab_name)
    ws.append_row(row, value_input_option="USER_ENTERED")


# ---------------------------------------------------------------------------
# Core processing logic
# ---------------------------------------------------------------------------

def process_message(
    service,
    message: dict,
    label_inbox_id: str,
    label_done_id: str,
    dry_run: bool,
    verbose: bool,
) -> bool:
    """
    Process one Gmail message. Returns True if an expense row was written.
    """
    msg_id  = message["id"]
    subject = get_subject(message)
    sender  = get_sender(message)

    if verbose:
        print(f"\n  Subject : {subject}")
        print(f"  From    : {sender}")

    # ── Determine property and flags from subject ────────────────────────────
    prop_from_subject = parse_property_from_subject(subject)
    is_tools          = is_tools_purchase(subject)
    utility_match     = match_utility_sender(sender, subject)
    is_utility_50     = utility_match is not None
    utility_vendor    = utility_match[0] if utility_match else None
    utility_category  = utility_match[1] if utility_match else None
    split_match       = match_split_sender(sender, subject)
    is_split          = split_match is not None
    split_vendor      = split_match[0] if split_match else None
    split_category    = split_match[1] if split_match else None

    # ── Try OCR on attachments first ─────────────────────────────────────────
    attachments = extract_attachments(service, message)
    ocr_result  = {}

    for file_bytes, filename, mime in attachments:
        if verbose:
            print(f"  Attachment: {filename} ({mime}, {len(file_bytes)} bytes)")
        result = parse_receipt(file_bytes, file_name=filename)
        if result.get("amount"):
            ocr_result = result
            if verbose:
                print(f"  OCR: vendor={result.get('vendor')}, "
                      f"date={result.get('date')}, amount={result.get('amount')}")
            break  # use first successful parse

    # ── Fallback: parse fields from email body ────────────────────────────────
    amount = ocr_result.get("amount")
    vendor = ocr_result.get("vendor")
    date   = ocr_result.get("date")

    body_text = extract_body_text(message)

    if not amount:
        amount = parse_amount_from_body(body_text)
        if amount and verbose:
            print(f"  Body fallback: amount={amount}")

    if not vendor:
        vendor = vendor_from_sender(sender)

    if not date:
        date = parse_date_from_body(body_text)
        if date and verbose:
            print(f"  Body fallback: date={date}")
    if not date:
        date = datetime.date.today()

    # ── Property: utility-sender wins → subject → body → default ─────────────
    subject_had_hint = any(alias in subject.lower() for alias in PROPERTY_ALIASES)
    if is_utility_50:
        prop   = "Winter Garden (Regal)"
        vendor = utility_vendor
    elif subject_had_hint:
        prop = prop_from_subject
    else:
        prop = parse_property_from_body(body_text) or prop_from_subject
    if verbose and not subject_had_hint and not is_utility_50:
        print(f"  Property resolved from body: {prop}")

    # ── Apply deduction rule (utility 50% or tools 80%) ──────────────────────
    full_amount = amount
    if amount and is_utility_50:
        save_amount = round(amount * 0.50, 2)
    elif amount and is_tools:
        save_amount = round(amount * 0.80, 2)
    else:
        save_amount = amount

    # ── Build description and notes ───────────────────────────────────────────
    description = subject.strip() or f"Email receipt from {vendor}"
    notes_parts = ["Auto-imported from Gmail"]
    if is_utility_50 and full_amount:
        notes_parts.append(f"Utility 50% rule: full bill ${full_amount:.2f}, saved ${save_amount:.2f}")
    elif is_tools and full_amount:
        notes_parts.append(f"Tools 80% rule: full receipt ${full_amount:.2f}, saved ${save_amount:.2f}")
    if not ocr_result.get("amount") and amount:
        notes_parts.append("NEEDS_REVIEW: amount from email body, not OCR")
    if not amount:
        notes_parts.append("NEEDS_REVIEW: could not extract amount — please fill in manually")
        save_amount = 0.0
    notes = " | ".join(notes_parts)

    # ── Determine category (split/utility senders force their mapped category, else keyword map) ─
    if is_split:
        category = split_category
        vendor = split_vendor
    elif is_utility_50:
        category = utility_category
    else:
        category = DEFAULT_CATEGORY
        subject_lower = subject.lower()
        category_map = {
            "repair":      "Repairs",
            "maintenance": "Cleaning and Maintenance",
            "pest":        "Cleaning and Maintenance",
            "clean":       "Cleaning and Maintenance",
            "insurance":   "Insurance",
            "utility":     "Utilities",
            "utilities":   "Utilities",
            "legal":       "Legal and Professional Fees",
            "advertising": "Advertising",
        }
        for kw, cat in category_map.items():
            if kw in subject_lower:
                category = cat
                break

    # ── Write to Sheets (split sender → one row per property; else single row) ─
    tag = "[DRY-RUN] " if dry_run else ""
    if is_split and save_amount:
        n = len(PROPERTIES)
        per_prop = round(save_amount / n, 2)
        split_notes = notes + f" | Split evenly across {n} properties: full bill ${save_amount:.2f}, ${per_prop:.2f} each"
        print(f"  {tag}→ SPLIT | {vendor} | ${save_amount:.2f} → ${per_prop:.2f} × {n} properties")
        for p in PROPERTIES:
            write_expense_row(
                property_name=p,
                date=date,
                vendor=vendor,
                amount=per_prop,
                category=category,
                description=description,
                notes=split_notes,
                dry_run=dry_run,
            )
    else:
        print(
            f"  {tag}→ {prop} | {vendor} | ${save_amount:.2f}"
            + (" (50% utility)" if is_utility_50 and full_amount else "")
            + (" (80% of tools)" if is_tools and full_amount else "")
            + (" ⚠ NEEDS_REVIEW" if "NEEDS_REVIEW" in notes else "")
        )
        write_expense_row(
            property_name=prop,
            date=date,
            vendor=vendor,
            amount=save_amount if save_amount else 0.0,
            category=category,
            description=description,
            notes=notes,
            dry_run=dry_run,
        )

    # ── Move email to done ────────────────────────────────────────────────────
    move_to_done(service, msg_id, label_inbox_id, label_done_id, dry_run)
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gmail receipt importer for Rental Manager")
    parser.add_argument("--setup",   action="store_true", help="Run Gmail OAuth flow (first-time setup)")
    parser.add_argument("--dry-run", action="store_true", help="Parse emails but do not write to Sheets")
    parser.add_argument("--verbose", action="store_true", help="Print detailed info per email")
    args = parser.parse_args()

    print("=" * 60)
    print("  Rental Manager — Gmail Receipt Poller")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("  MODE: DRY RUN — no writes")
    print("=" * 60)

    # Auth
    service = get_gmail_service()
    if args.setup:
        print("\n[SETUP] Gmail OAuth complete. Run without --setup to process emails.\n")
        return

    # Resolve label IDs (creates labels if they don't exist)
    label_inbox_id = get_or_create_label(service, LABEL_INBOX)
    label_done_id  = get_or_create_label(service, LABEL_DONE)

    # Find emails
    messages = list_unprocessed_messages(service, label_inbox_id)
    print(f"\nFound {len(messages)} email(s) labeled '{LABEL_INBOX}'\n")

    if not messages:
        print("Nothing to process.")
        return

    processed = 0
    for msg_stub in messages:
        full_msg = get_message(service, msg_stub["id"])
        subject = get_subject(full_msg)
        print(f"Processing: \"{subject}\"")
        try:
            ok = process_message(
                service, full_msg,
                label_inbox_id, label_done_id,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
            if ok:
                processed += 1
        except Exception as e:
            print(f"  [ERROR] Failed to process message: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    print(f"\nDone. Processed {processed}/{len(messages)} email(s).")


if __name__ == "__main__":
    main()
