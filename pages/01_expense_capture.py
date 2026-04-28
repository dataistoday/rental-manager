"""
pages/01_expense_capture.py — Expense Capture

Manual expense entry form. Saves to the Expenses tab with an IRS Schedule E category.
Use scripts/gmail_poller.py to import receipts automatically.
"""

import datetime
import streamlit as st
from utils.auth_gate import require_auth
import pandas as pd

from sheets.expenses import add_expense
from utils.cache import safe_get_expenses, show_fetch_error
from utils.formatting import format_currency, format_date
from drive.uploader import upload_image
from config import PROPERTIES, IRS_SCHEDULE_E_CATEGORIES, PAYMENT_METHODS, CAPITAL_IMPROVEMENT_CATEGORY

require_auth()

st.set_page_config(page_title="Expense Capture", page_icon="💸", layout="centered")
st.title("💸 Expense Capture")
st.caption("Log an expense to your Schedule E ledger.")

# ---------------------------------------------------------------------------
# Expense form
# ---------------------------------------------------------------------------
st.subheader("Expense Details")

_palm_harbor_idx = PROPERTIES.index("Palm Harbor") if "Palm Harbor" in PROPERTIES else 0
_supplies_idx = IRS_SCHEDULE_E_CATEGORIES.index("Supplies") if "Supplies" in IRS_SCHEDULE_E_CATEGORIES else 0

with st.form("expense_form", clear_on_submit=True):
    prop = st.selectbox("Property *", PROPERTIES, index=_palm_harbor_idx)

    col1, col2 = st.columns(2)
    with col1:
        expense_date = st.date_input("Date *", value=datetime.date.today())
    with col2:
        category = st.selectbox("Category (Schedule E) *", IRS_SCHEDULE_E_CATEGORIES, index=_supplies_idx)

    vendor = st.text_input(
        "Vendor / Payee *",
        placeholder="Home Depot, Joe's Plumbing…",
    )

    col3, col4 = st.columns(2)
    with col3:
        amount = st.number_input("Amount ($) *", min_value=0.0, step=0.01, format="%.2f")
    with col4:
        payment_method = st.selectbox("Payment Method", [""] + PAYMENT_METHODS)

    is_tools = st.checkbox(
        "Tools purchase (deduct 80%)",
        help="Check if this is a tool purchase. The saved amount will be 80% of the receipt total (IRS partial deductibility).",
    )
    if is_tools and amount > 0:
        st.info(f"Deductible amount: **{format_currency(amount * 0.80)}** (80% of {format_currency(amount)})")

    is_capital_improvement = st.checkbox(
        "Capital improvement (depreciate, don't expense)",
        help="Check for things like new roof, HVAC, water heater, kitchen remodel, additions. "
             "These are capitalized and depreciated over 27.5 years — they do NOT go on Schedule E "
             "as a current-year expense. Row will be tagged for your CPA's depreciation schedule.",
    )
    if is_capital_improvement:
        st.warning(
            f"This row will be saved under category **{CAPITAL_IMPROVEMENT_CATEGORY}** "
            "(not Schedule E). It'll be excluded from current-year expense totals and surfaced "
            "in the year-end depreciation list for your CPA.",
            icon="🏗️",
        )

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
                cap_note = "CAPITAL IMPROVEMENT — for depreciation schedule (Form 4562)" if is_capital_improvement else ""
                final_notes = "\n".join(filter(None, [cap_note, tools_note, notes.strip()]))
                save_category = CAPITAL_IMPROVEMENT_CATEGORY if is_capital_improvement else category

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
                    category=save_category,
                    description=description.strip(),
                    receipt_url=receipt_url,
                    payment_method=payment_method,
                    notes=final_notes,
                )
                st.success(
                    f"Saved! {format_currency(save_amount)} · {save_category} · {prop}"
                    + (" (80% of tools receipt)" if is_tools else "")
                    + (" — flagged for depreciation" if is_capital_improvement else "")
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
