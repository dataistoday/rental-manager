# Rental Manager — CLAUDE.md

Florida rental portfolio management app. Mobile-first Streamlit app backed by Google Sheets and Google Drive.

## Properties
- Winter Garden (Regal)
- Winter Garden (Charlotte)
- Palm Harbor
- Tampa

## Tech Stack
- **Frontend:** Streamlit (Python) — `streamlit run app.py`
- **Database:** Google Sheets via `gspread`
- **File Storage:** Google Drive via `google-api-python-client`
- **OCR:** Veryfi API (~$0.08/receipt, pay-per-use) — sign up at veryfi.com, add 3 keys to `.env`
- **Deployment:** Local-first; cloud-ready for Streamlit Community Cloud

## Property Addresses
- **Winter Garden (Regal):** 13 Regal Pl
- **Winter Garden (Charlotte):** unknown
- **Palm Harbor:** 254 W Canal Dr
- **Tampa:** 8723 Elmwood Lane

## Project Structure
```
app.py                  # Entry point + password gate + lease renewal alert banners
config.py               # ALL constants — properties, IRS categories, rates, sheet tab names
.env                    # Local secrets (gitignored — copy from .env.example)
credentials.json        # Google Service Account key (gitignored)
gmail_oauth_client.json # Gmail OAuth Desktop App credentials (gitignored)
gmail_token.json        # Gmail OAuth token — auto-generated on first --setup run (gitignored)

auth/google_auth.py     # Dual-mode auth: .env locally, st.secrets on Cloud
sheets/
  client.py             # get_worksheet(), append_row(), update_row() — all writes go here
  expenses.py           # Expenses tab
  mileage.py            # Mileage tab
  maintenance.py        # Maintenance tab (has update_maintenance_status for in-place edits)
  insurance.py          # Insurance tab (read-only)
  vendors.py            # Vendors tab
  tenants.py            # Tenants tab
  inspections.py        # Inspections tab
drive/uploader.py       # upload_file(), upload_image(), upload_pdf(),
                        # upload_photo_for_property(), list_property_photos(),
                        # get_or_create_subfolder()
ocr/receipt_parser.py   # parse_receipt(bytes, file_name) → {vendor, date, amount, confidence}
utils/formatting.py     # format_currency(), format_phone(), status_badge(), etc.
utils/cache.py          # safe_get_*() wrappers — graceful degradation on Sheets failure

pages/
  01_expense_capture.py   # Camera/upload (jpg/png/pdf) → OCR → IRS Schedule E form
                          # Defaults: Palm Harbor, Supplies; Tools checkbox applies 80% deduction
  02_mileage_tracker.py   # Odometer → miles + deduction at IRS rate; vehicle dropdown; defaults to Tampa
  03_maintenance_log.py   # Issue log, status updates, photo uploads to Drive
  04_insurance_vault.py   # Read-only policy cards (populated manually in Sheets)
  05_vendor_directory.py  # Filterable contractor list
  06_tenant_log.py        # Chronological tenant interaction log
  07_tax_summary.py       # Schedule E dashboard by year & property, CSV export
  08_lease_renewals.py    # Lease expiration alerts, color-coded by urgency
  09_inspection_log.py    # Move-in/out, annual, ad-hoc inspections + photos
  11_property_photos.py   # Zillow/listing photos, auto-organized by property in Drive

scripts/
  gmail_poller.py         # Standalone Gmail receipt importer (run on demand or via Task Scheduler)
                          # Watches 'rental-receipts' Gmail label, parses vendor/date/amount,
                          # writes to Expenses sheet. Uses OAuth (gmail_oauth_client.json).
                          # Run: py scripts/gmail_poller.py [--dry-run] [--verbose] [--setup]
```

## Google Sheets Schema (one spreadsheet, 7 tabs)
- **Expenses:** timestamp, property, date, vendor, amount, category, description, receipt_url, payment_method, notes
  (Utility bills are logged here with category=`Utilities` — no separate Utilities tab.)
- **Mileage:** timestamp, date, property, purpose, start_odometer, end_odometer, miles, irs_rate, deduction_amount, notes, vehicle
- **Maintenance:** id, timestamp, last_updated, property, issue_title, description, status, priority, contractor, estimated_cost, actual_cost, photo_urls, resolution_notes
- **Insurance:** property, policy_number, insurer, agent_name, agent_phone, agent_email, premium_annual, renewal_date, coverage_type, doc_url, notes
- **Vendors:** timestamp, company_name, contact_name, phone, email, trade, properties_served, hourly_rate, rating, notes, last_used_date
- **Tenants:** timestamp, property, tenant_name, lease_start, lease_end, monthly_rent, security_deposit, entry_type, entry_date, subject, body, doc_url
- **Inspections:** id, timestamp, property, inspection_type, inspection_date, inspector, condition_overall, notes, action_items, photo_urls

## Google Drive Folder Structure
```
Receipts/               ← DRIVE_FOLDER_RECEIPTS
Maintenance Photos/     ← DRIVE_FOLDER_MAINTENANCE
Documents/              ← DRIVE_FOLDER_DOCUMENTS
Property Photos/        ← DRIVE_FOLDER_PHOTOS (parent folder)
  Winter Garden (Regal)/        ← auto-created on first upload
  Winter Garden (Charlotte)/    ← auto-created on first upload
  Palm Harbor/                  ← auto-created on first upload
  Tampa/                        ← auto-created on first upload
```

## Key Design Rules
- **`config.py` is the only place** to add properties, IRS categories, vendor trades, inspection types, or vehicles
- **Never hardcode property names** in page files — always import from `config.PROPERTIES`
- **All writes** go through `sheets/client.py` (`append_row` / `update_row`) — never call gspread directly from pages
- **All reads** go through `utils/cache.py` `safe_get_*()` functions for graceful degradation
- **Mobile-first UI:** `layout="centered"`, all buttons `use_container_width=True`, single-column forms
- **Dual-mode secrets:** `auth/google_auth.py` tries `st.secrets` first (cloud), then `credentials.json` (local)
- **Drive subfolders** for property photos are created automatically via `get_or_create_subfolder()` — no manual folder setup needed beyond the parent
- **gmail_poller.py is standalone** — it does NOT import from `sheets/client.py` or `auth/google_auth.py` (both have Streamlit dependencies). It writes to Sheets directly via gspread with the service account.

## Gmail Poller — How It Works
- Watches Gmail label `rental-receipts` (configurable in `.env` as `GMAIL_LABEL_NAME`)
- For each email: tries Veryfi OCR on attachments first, falls back to HTML body parsing
- Property detection order: subject keyword → body address hint → default (Palm Harbor)
- Amount detection: labeled regex patterns → frequency fallback (most common non-zero `$XX.XX`)
- Processed emails moved to `rental-receipts-done` label automatically
- Tools 80% deduction: add `TOOLS` to the email subject when forwarding

### Subject line shortcuts
| Subject contains | Property |
|---|---|
| `PH`, `palm harbor`, `254 w canal`, `canal dr` | Palm Harbor |
| `TPA`, `tampa`, `8723 elmwood`, `elmwood` | Tampa |
| `WGR`, `regal`, `13 regal` | Winter Garden (Regal) |
| `WGC`, `charlotte` | Winter Garden (Charlotte) |
| `TOOLS` | applies 80% deduction to saved amount |

### Body address hints (auto-detected, no subject edit needed)
| Body contains | Property |
|---|---|
| `8723 elmwood` or `elmwood lane` | Tampa |
| `254 w canal` or `canal dr` | Palm Harbor |
| `13 regal` or `regal` | Winter Garden (Regal) |

### Category auto-detection (from subject keywords)
`pest`, `clean` → Cleaning and Maintenance | `repair`, `maintenance` → Repairs | `insurance` → Insurance | `utility` → Utilities

### Winter Garden (Regal) utility senders — auto 50% rule
Emails from (or forwarded with subject referencing) these vendors are forced to
Winter Garden (Regal) + 50% deduction (full amount stamped in Notes). The Schedule E
category is per-sender so each bill rolls up to the correct IRS line item:
| Sender/subject contains | Vendor saved | Schedule E category |
|---|---|---|
| `duke-energy`, `duke energy` | Duke Energy | Utilities |
| `metronet`, `metro net` | Metro Net | Utilities |
| `cityofwintergarden`, `winter garden utilities`, `cwgdn` | Winter Garden Utilities | Utilities |
| `rowland pest`, `rowlandpest` | Rowland Pest Control | Cleaning and Maintenance |

Rule lives in `UTILITY_50_SENDERS` in `scripts/gmail_poller.py` — values are
`(vendor, category)` tuples. Add new senders there.

### Portfolio-wide senders — auto-split across all properties
Emails from these senders are split evenly across all `PROPERTIES` — one expense
row per property at amount ÷ N. Good for rental-management software and other
portfolio-level services:
| Sender/subject contains | Vendor saved | Schedule E category |
|---|---|---|
| `avail.co`, `avail ` | Avail | Management Fees |

Rule lives in `SPLIT_SENDERS` in `scripts/gmail_poller.py`. Full amount and
per-property share are stamped in the Notes column on each row.

## Running Locally
```bash
py -m venv .venv          # Windows: use "py" not "python"
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py      # → http://localhost:8501
```
Phone access (same WiFi): `http://YOUR_PC_IP:8501`

## Setup Status (as of 2026-04-16)
- [x] Google Cloud project created (`rental-manager-493419`) with Sheets + Drive APIs enabled
- [x] Service Account created → `credentials.json` in project root
- [x] `.env` filled in (SPREADSHEET_ID, Drive folder IDs, Veryfi keys)
- [x] Google Spreadsheet shared with service account (`rental-manager@rental-manager-493419.iam.gserviceaccount.com`)
- [x] Veryfi account configured — keys in `.env`
- [x] App running locally
- [x] Google Sheet tab names confirmed: `Expenses`, `Mileage`, `Maintenance`, `Insurance`, `Vendors`, `Tenants`
- [x] 3 Drive folders shared with service account email
- [x] `APP_PASSWORD` set
- [x] Add `Inspections` tab to Google Sheet
- [x] Create "Property Photos" Drive folder → share with service account → add ID to `.env` as `DRIVE_FOLDER_PHOTOS`
- [x] Gmail API enabled in Google Cloud Console
- [x] OAuth 2.0 Desktop Client created → `gmail_oauth_client.json` in project root
- [x] Gmail OAuth consent screen configured (External, test user: dataistoday@gmail.com)
- [x] Gmail poller authorized → `gmail_token.json` saved
- [x] Gmail label `rental-receipts` created
- [x] Poller tested successfully — Rowland Pest email parsed correctly
- [x] Utility 50% rule wired up for Duke Energy, Metro Net, Winter Garden Utilities (all → Winter Garden (Regal), category=Utilities)

## Streamlit Community Cloud
- [x] GitHub repo created: `dataistoday/rental-manager`
- [x] Deployed to Streamlit Community Cloud (`master` branch, `app.py`)
- [x] Secrets configured in Streamlit Cloud dashboard (service account, Drive folder IDs, Veryfi keys, APP_PASSWORD)
- [x] App live and credentials verified working

## Expense Capture Defaults (as of 2026-04-16)
- Default property: **Palm Harbor**
- Default category: **Supplies**
- Tools checkbox: saves 80% of receipt total; stamps full amount in Notes

## Gmail Poller — Parsing Notes
- Self-forwarded emails (from your own Gmail): vendor extracted from subject line, not From: header
- Subject format for self-forwards: `[property code] [TOOLS] Vendor Name` e.g. `PH Home Depot`, `tools PH Harbor Freight`
- Amount fallback: if no labeled pattern matches, uses frequency analysis (most common non-zero `$XX.XX` in email body)
- HTML emails: tags are stripped before regex matching so amounts split across table cells are found

## Mileage Tracker Notes
- Refresh button on Trip History clears the 5-minute read cache instantly — use this after manual Sheet edits
- Manually backfilled rows: dates entered as `2/1` style are fine if Google Sheets stores them as actual dates (right-aligned = date, left-aligned = text)
- Deduction amount on manually entered rows: fill as `miles × 0.70`; app will calculate from miles column if deduction_amount is blank

## Gmail Poller — Next Steps
- [ ] Set up Windows Task Scheduler to run `py scripts/gmail_poller.py` every 5 minutes
- [ ] Set up Gmail filters to auto-label receipts from frequent vendors:
    - Rowland Pest, Home Depot, Lowes, etc. → apply `rental-receipts`
    - `duke-energyalert.com`, `metronet`, `cityofwintergarden` → apply `rental-receipts` (will auto-trigger 50% utility rule)
- [ ] Add Charlotte property street address to `BODY_PROPERTY_HINTS` and `PROPERTY_ALIASES` in `scripts/gmail_poller.py` once known

## Known Sender Domains (confirmed 2026-04-16)
- **Duke Energy billing:** `DukeEnergyPayConfirmation@duke-energyalert.com` — caught by `duke-energy` substring match
- *(add Metro Net and Winter Garden Utilities domains here once first bill arrives)*
