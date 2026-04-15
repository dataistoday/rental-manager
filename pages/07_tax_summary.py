"""
pages/07_tax_summary.py — Tax Summary Dashboard

Pulls from Expenses and Mileage tabs to produce a Schedule E-ready
summary by property and year. Shows:
  - Total deductions by IRS category (Schedule E line items)
  - Mileage deduction (auto & travel)
  - Per-property breakdown
  - Downloadable CSV for your accountant
"""

import datetime
import pandas as pd
import streamlit as st

from utils.cache import safe_get_expenses, safe_get_mileage, show_fetch_error
from utils.formatting import format_currency
from config import PROPERTIES, IRS_SCHEDULE_E_CATEGORIES

st.set_page_config(page_title="Tax Summary", page_icon="🧾", layout="centered")
st.title("🧾 Tax Summary")
st.caption("Schedule E deduction summary by property and year.")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
current_year = datetime.date.today().year
year = st.selectbox(
    "Tax Year",
    options=list(range(current_year, current_year - 6, -1)),
    index=0,
)
property_filter = st.selectbox("Property", ["All Properties"] + PROPERTIES)

st.markdown("---")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
exp_df, exp_err = safe_get_expenses()
mil_df, mil_err = safe_get_mileage()
show_fetch_error(exp_err or mil_err)

# ---------------------------------------------------------------------------
# Process expenses
# ---------------------------------------------------------------------------
expenses_total = 0.0
cat_totals: dict[str, float] = {cat: 0.0 for cat in IRS_SCHEDULE_E_CATEGORIES}
exp_by_prop: dict[str, float] = {p: 0.0 for p in PROPERTIES}

if exp_df is not None and not exp_df.empty:
    df = exp_df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Normalize date column
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].dt.year == year]

    if property_filter != "All Properties":
        df = df[df["property"] == property_filter]

    for _, row in df.iterrows():
        amt = float(row["amount"])
        cat = row.get("category", "Other")
        prop = row.get("property", "")
        expenses_total += amt
        if cat in cat_totals:
            cat_totals[cat] += amt
        else:
            cat_totals["Other"] += amt
        if prop in exp_by_prop:
            exp_by_prop[prop] += amt

# ---------------------------------------------------------------------------
# Process mileage
# ---------------------------------------------------------------------------
mileage_total_miles = 0.0
mileage_deduction = 0.0
mil_by_prop: dict[str, float] = {p: 0.0 for p in PROPERTIES}

if mil_df is not None and not mil_df.empty:
    mdf = mil_df.copy()
    mdf["deduction_amount"] = pd.to_numeric(mdf["deduction_amount"], errors="coerce").fillna(0)
    mdf["miles"] = pd.to_numeric(mdf["miles"], errors="coerce").fillna(0)
    mdf["date"] = pd.to_datetime(mdf["date"], errors="coerce")
    mdf = mdf[mdf["date"].dt.year == year]

    if property_filter != "All Properties":
        mdf = mdf[mdf["property"] == property_filter]

    mileage_total_miles = mdf["miles"].sum()
    mileage_deduction = mdf["deduction_amount"].sum()

    for _, row in mdf.iterrows():
        prop = row.get("property", "")
        if prop in mil_by_prop:
            mil_by_prop[prop] += float(row["deduction_amount"])

    # Roll mileage deduction into "Auto and Travel" category total
    cat_totals["Auto and Travel"] += mileage_deduction

grand_total = expenses_total + mileage_deduction

# ---------------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------------
prop_label = property_filter if property_filter != "All Properties" else "All Properties"
st.subheader(f"{year} — {prop_label}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Deductions", format_currency(grand_total))
col2.metric("Expense Deductions", format_currency(expenses_total))
col3.metric("Mileage Deduction", f"{format_currency(mileage_deduction)}  \n({mileage_total_miles:,.1f} mi)")

st.markdown("---")

# ---------------------------------------------------------------------------
# Schedule E breakdown by category
# ---------------------------------------------------------------------------
st.subheader("Schedule E Breakdown")

rows = [
    {"Category": cat, "Amount": amt}
    for cat, amt in cat_totals.items()
    if amt > 0
]
rows_sorted = sorted(rows, key=lambda r: r["Amount"], reverse=True)

if rows_sorted:
    summary_df = pd.DataFrame(rows_sorted)
    summary_df["Amount"] = summary_df["Amount"].apply(format_currency)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    st.info(f"No expenses recorded for {year}.", icon="ℹ️")

# ---------------------------------------------------------------------------
# Per-property breakdown (only shown when "All Properties" selected)
# ---------------------------------------------------------------------------
if property_filter == "All Properties":
    st.markdown("---")
    st.subheader("By Property")

    prop_rows = []
    for prop in PROPERTIES:
        total = exp_by_prop[prop] + mil_by_prop[prop]
        if total > 0:
            prop_rows.append({
                "Property": prop,
                "Expenses": format_currency(exp_by_prop[prop]),
                "Mileage": format_currency(mil_by_prop[prop]),
                "Total": format_currency(total),
            })

    if prop_rows:
        st.dataframe(pd.DataFrame(prop_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No data to show.", icon="ℹ️")

# ---------------------------------------------------------------------------
# Download CSV for accountant
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Export for Accountant")

if rows_sorted or (property_filter == "All Properties" and any(
    exp_by_prop[p] + mil_by_prop[p] > 0 for p in PROPERTIES
)):
    # Build a flat export with raw numbers
    export_rows = []
    for cat, amt in cat_totals.items():
        if amt > 0:
            export_rows.append({
                "Tax Year": year,
                "Property": prop_label,
                "Schedule E Category": cat,
                "Amount": round(amt, 2),
                "Note": f"Includes {mileage_total_miles:,.1f} mi @ IRS rate" if cat == "Auto and Travel" and mileage_deduction > 0 else "",
            })

    export_df = pd.DataFrame(export_rows)
    csv = export_df.to_csv(index=False)

    st.download_button(
        label=f"Download {year} Summary CSV",
        data=csv,
        file_name=f"schedule_e_{year}_{prop_label.replace(' ', '_').replace('(', '').replace(')', '')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
else:
    st.info("No data to export yet.", icon="ℹ️")
