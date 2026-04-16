# config.py — Single source of truth for all app constants.
# To add a property, IRS category, or vendor trade, edit only this file.

PROPERTIES = [
    "Winter Garden (Regal)",
    "Winter Garden (Charlotte)",
    "Palm Harbor",
    "Tampa",
]

SHEET_TABS = {
    "expenses":    "Expenses",
    "mileage":     "Mileage",
    "maintenance": "Maintenance",
    "insurance":   "Insurance",
    "vendors":     "Vendors",
    "tenants":     "Tenants",
    "inspections": "Inspections",
    "utilities":   "Utilities",
}

# IRS Schedule E categories — used on every expense entry
IRS_SCHEDULE_E_CATEGORIES = [
    "Advertising",
    "Auto and Travel",
    "Cleaning and Maintenance",
    "Commissions",
    "Insurance",
    "Legal and Professional Fees",
    "Management Fees",
    "Mortgage Interest",
    "Other Interest",
    "Repairs",
    "Supplies",
    "Taxes",
    "Utilities",
    "Depreciation",
    "Other",
]

# IRS standard mileage rate — update each January
IRS_MILEAGE_RATE_2024 = 0.67
IRS_MILEAGE_RATE_2025 = 0.70
IRS_MILEAGE_RATE_2026 = 0.70  # TODO: confirm 2026 rate at irs.gov when announced
IRS_MILEAGE_RATE_CURRENT = IRS_MILEAGE_RATE_2026

MAINTENANCE_STATUSES = ["Open", "In Progress", "Resolved"]
MAINTENANCE_PRIORITIES = ["Low", "Medium", "High", "Emergency"]

VENDOR_TRADES = [
    "Plumber",
    "HVAC",
    "Electrician",
    "Handyman",
    "Roofer",
    "Landscaper",
    "Pest Control",
    "Painter",
    "Appliance Repair",
    "Other",
]

PAYMENT_METHODS = ["Card", "Cash", "Check", "Zelle", "Venmo", "Bank Transfer"]

INSPECTION_TYPES = [
    "Move-In",
    "Move-Out",
    "Annual",
    "Quarterly",
    "Drive-By",
    "Insurance",
    "Other",
]

INSPECTION_CONDITIONS = ["Excellent", "Good", "Fair", "Poor"]

UTILITY_TYPES = [
    "Electric",
    "Water / Sewer",
    "Gas",
    "Trash / Recycling",
    "Cable / Internet",
    "HOA",
    "Other",
]

ENTRY_TYPES = [
    "Note",
    "Legal Notice",
    "Payment",
    "Maintenance Request",
    "Lease Renewal",
    "Move-In",
    "Move-Out",
    "Other",
]

MILEAGE_PURPOSES = [
    "Inspection",
    "Repair / Maintenance",
    "Tenant Meeting",
    "Showing / Vacancy",
    "Supply Run",
    "Bank / Financial",
    "Other",
]

# Vehicles used for mileage tracking — update with your actual vehicle names
VEHICLES = [
    "Tacoma",
    "Mini",
    "FJ",
    "Camper",
]

# Google Drive folder IDs — fill these in after Google Cloud setup
# See .env.example for the environment variable names
DRIVE_FOLDERS = {
    "receipts":    "REPLACE_WITH_DRIVE_FOLDER_ID",
    "maintenance": "REPLACE_WITH_DRIVE_FOLDER_ID",
    "documents":   "REPLACE_WITH_DRIVE_FOLDER_ID",
    "photos":      "REPLACE_WITH_DRIVE_FOLDER_ID",
}

# Google Spreadsheet ID — fill in after creating the sheet
# See .env.example for the environment variable name
SPREADSHEET_ID = "REPLACE_WITH_SPREADSHEET_ID"

# Sheets API read cache TTL in seconds (5 minutes)
CACHE_TTL_SECONDS = 300
