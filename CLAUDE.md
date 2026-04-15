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

## Project Structure
```
app.py                  # Entry point + password gate + lease renewal alert banners
config.py               # ALL constants — properties, IRS categories, rates, sheet tab names
.env                    # Local secrets (gitignored — copy from .env.example)
credentials.json        # Google Service Account key (gitignored)

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
  utilities.py          # Utilities tab
drive/uploader.py       # upload_file(), upload_image(), upload_pdf(),
                        # upload_photo_for_property(), list_property_photos(),
                        # get_or_create_subfolder()
ocr/receipt_parser.py   # parse_receipt(bytes, file_name) → {vendor, date, amount, confidence}
utils/formatting.py     # format_currency(), format_phone(), status_badge(), etc.
utils/cache.py          # safe_get_*() wrappers — graceful degradation on Sheets failure

pages/
  01_expense_capture.py   # Camera/upload (jpg/png/pdf) → OCR → IRS Schedule E form
  02_mileage_tracker.py   # Odometer → miles + deduction at IRS rate
  03_maintenance_log.py   # Issue log, status updates, photo uploads to Drive
  04_insurance_vault.py   # Read-only policy cards (populated manually in Sheets)
  05_vendor_directory.py  # Filterable contractor list
  06_tenant_log.py        # Chronological tenant interaction log
  07_tax_summary.py       # Schedule E dashboard by year & property, CSV export
  08_lease_renewals.py    # Lease expiration alerts, color-coded by urgency
  09_inspection_log.py    # Move-in/out, annual, ad-hoc inspections + photos
  10_utility_tracker.py   # Utility bills by property, unpaid alerts, YTD totals
  11_property_photos.py   # Zillow/listing photos, auto-organized by property in Drive
```

## Google Sheets Schema (one spreadsheet, 8 tabs)
- **Expenses:** timestamp, property, date, vendor, amount, category, description, receipt_url, payment_method, notes
- **Mileage:** timestamp, date, property, purpose, start_odometer, end_odometer, miles, irs_rate, deduction_amount, notes
- **Maintenance:** id, timestamp, last_updated, property, issue_title, description, status, priority, contractor, estimated_cost, actual_cost, photo_urls, resolution_notes
- **Insurance:** property, policy_number, insurer, agent_name, agent_phone, agent_email, premium_annual, renewal_date, coverage_type, doc_url, notes
- **Vendors:** timestamp, company_name, contact_name, phone, email, trade, properties_served, hourly_rate, rating, notes, last_used_date
- **Tenants:** timestamp, property, tenant_name, lease_start, lease_end, monthly_rent, security_deposit, entry_type, entry_date, subject, body, doc_url
- **Inspections:** id, timestamp, property, inspection_type, inspection_date, inspector, condition_overall, notes, action_items, photo_urls
- **Utilities:** timestamp, property, utility_type, provider, account_number, billing_period, amount, due_date, paid_date, notes

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
- **`config.py` is the only place** to add properties, IRS categories, vendor trades, inspection types, or utility types
- **Never hardcode property names** in page files — always import from `config.PROPERTIES`
- **All writes** go through `sheets/client.py` (`append_row` / `update_row`) — never call gspread directly from pages
- **All reads** go through `utils/cache.py` `safe_get_*()` functions for graceful degradation
- **Mobile-first UI:** `layout="centered"`, all buttons `use_container_width=True`, single-column forms
- **Dual-mode secrets:** `auth/google_auth.py` tries `st.secrets` first (cloud), then `credentials.json` (local)
- **Drive subfolders** for property photos are created automatically via `get_or_create_subfolder()` — no manual folder setup needed beyond the parent

## Running Locally
```bash
py -m venv .venv          # Windows: use "py" not "python"
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py      # → http://localhost:8501
```
Phone access (same WiFi): `http://YOUR_PC_IP:8501`

## Setup Status (as of 2026-04-15)
- [x] Google Cloud project created (`rental-manager-493419`) with Sheets + Drive APIs enabled
- [x] Service Account created → `credentials.json` in project root
- [x] `.env` filled in (SPREADSHEET_ID, Drive folder IDs, Veryfi keys)
- [x] Google Spreadsheet shared with service account (`rental-manager@rental-manager-493419.iam.gserviceaccount.com`)
- [x] Veryfi account configured — keys in `.env`
- [x] App running locally
- [x] Google Sheet tab names confirmed: `Expenses`, `Mileage`, `Maintenance`, `Insurance`, `Vendors`, `Tenants`
- [x] 3 Drive folders shared with service account email
- [x] `APP_PASSWORD` set
- [ ] Add `Inspections` tab to Google Sheet
- [ ] Add `Utilities` tab to Google Sheet
- [ ] Create "Property Photos" Drive folder → share with service account → add ID to `.env` as `DRIVE_FOLDER_PHOTOS`

## Streamlit Community Cloud (future)
- No system packages needed — Veryfi runs via API, nothing to install on the server
- Paste service account JSON as `[GOOGLE_SERVICE_ACCOUNT]` TOML block in Streamlit secrets
- Add `VERYFI_CLIENT_ID`, `VERYFI_CLIENT_SECRET`, `VERYFI_API_KEY` to Streamlit secrets
- Add `DRIVE_FOLDER_PHOTOS` to Streamlit secrets
- Set `APP_PASSWORD` in secrets to enable the password gate
