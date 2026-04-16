"""
pages/01_expense_capture.py — Expense Capture

Most powerful page: use your phone camera or upload a receipt image,
OCR extracts vendor/date/amount, pre-fills the form, and saves to the
Expenses tab with an IRS Schedule E category.
"""

import datetime
import streamlit as st
import pandas as pd

from sheets.expenses import add_expense
from utils.cache import safe_get_expenses, show_fetch_error
from utils.formatting import format_currency, format_date
from drive.uploader import upload_image
from ocr.receipt_parser import parse_receipt, OCR_AVAILABLE
from config import PROPERTIES, IRS_SCHEDULE_E_CATEGORIES, PAYMENT_METHODS

st.set_page_config(page_title="Expense Capture", page_icon="💸", layout="centered")
st.title("💸 Expense Capture")
st.caption("Scan a receipt → auto-fill → save to Schedule E ledger.")

# ---------------------------------------------------------------------------
# Receipt scanner
# ---------------------------------------------------------------------------
st.subheader("Scan Receipt (Optional)")

ocr_result = {}

if not OCR_AVAILABLE:
    st.info(
        "Receipt scanning is not configured — fill in the form manually below.  \n"
        "Add your Veryfi credentials to `.env` to enable OCR.",
        icon="ℹ️",
    )
else:
    scan_tab, upload_tab = st.tabs(["📷 Camera", "📁 Upload File"])
    image_bytes = None
    receipt_file_name = "receipt.jpg"

    with scan_tab:
        camera_image = st.camera_input("Point camera at receipt")
        if camera_image:
            image_bytes = camera_image.getvalue()

    with upload_tab:
        uploaded = st.file_uploader("Upload receipt image or PDF", type=["jpg", "jpeg", "png", "pdf"])
        if uploaded:
            image_bytes = uploaded.read()
            receipt_file_name = uploaded.name

    if image_bytes:
        with st.spinner("Reading receipt…"):
            ocr_result = parse_receipt(image_bytes, file_name=receipt_file_name)

        if ocr_result.get("amount"):
            st.success(
                f"Extracted: **{ocr_result.get('vendor', '?')}** · "
                f"**{format_date(ocr_result.get('date'))}** · "
                f"**{format_currency(ocr_result.get('amount'))}**"
            )
        else:
            st.warning("OCR couldn't extract a total — check the fields below.", icon="⚠️")

st.markdown("---")

# ---------------------------------------------------------------------------
# Expense form — pre-filled from OCR where available
# ---------------------------------------------------------------------------
st.subheader("Expense Details")

# Helper: show ⚠️ label when OCR wasn't confident
def field_label(label: str, key: str) -> str:
    conf = ocr_result.get("confidence", {})
    if ocr_result and not conf.get(key, True):
        return f"{label} ⚠️"
    return label


_palm_harbor_idx = PROPERTIES.index("Palm Harbor") if "Palm Harbor" in PROPERTIES else 0
_supplies_idx = IRS_SCHEDULE_E_CATEGORIES.index("Supplies") if "Supplies" in IRS_SCHEDULE_E_CATEGORIES else 0

with st.form("expense_form", clear_on_submit=True):
    prop = st.selectbox("Property *", PROPERTIES, index=_palm_harbor_idx)

    col1, col2 = st.columns(2)
    with col1:
        expense_date = st.date_input(
            field_label("Date *", "date"),
            value=ocr_result.get("date") or datetime.date.today(),
        )
    with col2:
        category = st.selectbox("Category (Schedule E) *", IRS_SCHEDULE_E_CATEGORIES, index=_supplies_idx)

    vendor = st.text_input(
        field_label("Vendor / Payee *", "vendor"),
        value=ocr_result.get("vendor") or "",
        placeholder="Home Depot, Joe's Plumbing…",
    )

    col3, col4 = st.columns(2)
    with col3:
        amount = st.number_input(
            field_label("Amount ($) *", "amount"),
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=float(ocr_result.get("amount") or 0.0),
        )
    with col4:
        payment_method = st.selectbox("Payment Method", [""] + PAYMENT_METHODS)

    is_tools = st.checkbox(
        "Tools purchase (deduct 80%)",
        help="Check if this is a tool purchase. The saved amount will be 80% of the receipt total (IRS partial deductibility).",
    )
    if is_tools and amount > 0:
        st.info(f"Deductible amount: **{format_currency(amount * 0.80)}** (80% of {format_currency(amount)})")

    description = st.text_input("Description", placeholder="Brief description of what was purchased")
    notes = st.text_input("Notes (optional)")

    # Receipt image upload (stored to Drive)
    receipt_file = st.file_uploader(
        "Receipt Image (for Drive vault)",
        type=["jpg", "jpeg", "png", "pdf"],
        help="Upload the receipt to attach a Drive link to this expense record.",
    )

    submitted = st.form_submit_button("Save Expense", use_container_width=True)

    if submitted:
        errors = []
        if not vendor.strip():
            errors.append("Vendor is required.")
        if amount <= 0:
            errors.append("Amount must be greater than $0.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                save_amount = round(amount * 0.80, 2) if is_tools else amount
                tools_note = f"Tools (full receipt: {format_currency(amount)}, 80% deducted)" if is_tools else ""
                final_notes = "\n".join(filter(None, [tools_note, notes.strip()]))

                receipt_url = ""
                if receipt_file:
                    ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"{prop.replace(' ', '_')}_{ts_str}_{receipt_file.name}"
                    mime = "application/pdf" if receipt_file.name.lower().endswith(".pdf") else "image/jpeg"
                    receipt_url = upload_image(receipt_file.read(), fname, folder_key="receipts")

                add_expense(
                    property_name=prop,
                    date=expense_date,
                    vendor=vendor.strip(),
                    amount=save_amount,
                    category=category,
                    description=description.strip(),
                    receipt_url=receipt_url,
                    payment_method=payment_method,
                    notes=final_notes,
                )
                st.success(
                    f"Saved! {format_currency(save_amount)} · {category} · {prop}"
                    + (" (80% of tools receipt)" if is_tools else "")
                )
            except Exception as e:
                st.error(f"Failed to save: {e}")

# ---------------------------------------------------------------------------
# Expense history
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Recent Expenses")

df, err = safe_get_expenses()
show_fetch_error(err)

if df is None or df.empty:
    st.info("No expenses logged yet.", icon="ℹ️")
    st.stop()

# Filters
col1, col2 = st.columns(2)
with col1:
    prop_f = st.selectbox("Property", ["All"] + PROPERTIES, key="exp_prop")
with col2:
    cat_f = st.selectbox("Category", ["All"] + IRS_SCHEDULE_E_CATEGORIES, key="exp_cat")

filtered = df.copy()
if prop_f != "All":
    filtered = filtered[filtered["property"] == prop_f]
if cat_f != "All":
    filtered = filtered[filtered["category"] == cat_f]

# Summary
total = pd.to_numeric(filtered["amount"], errors="coerce").sum()
st.metric("Total (filtered)", format_currency(total))

# Table
display_cols = ["date", "property", "vendor", "amount", "category", "receipt_url"]
available = [c for c in display_cols if c in filtered.columns]
display_df = filtered[available].copy()
display_df.columns = [c.replace("_", " ").title() for c in available]
if "Amount" in display_df.columns:
    display_df["Amount"] = pd.to_numeric(display_df["Amount"], errors="coerce").apply(
        lambda x: format_currency(x) if pd.notna(x) else ""
    )
if "Receipt Url" in display_df.columns:
    display_df = display_df.rename(columns={"Receipt Url": "Receipt"})

st.dataframe(display_df, use_container_width=True, hide_index=True)
