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
from utils.auth_gate import require_auth

from utils.cache import safe_get_expenses, safe_get_mileage, safe_get_rent_income, show_fetch_error
from utils.formatting import format_currency
from utils.date_normalize import normalize_date_column
from config import PROPERTIES, IRS_SCHEDULE_E_CATEGORIES, CAPITAL_IMPROVEMENT_CATEGORY

require_auth()

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
rent_df, rent_err = safe_get_rent_income()
show_fetch_error(exp_err or mil_err or rent_err)

# ---------------------------------------------------------------------------
# Process rent income
# ---------------------------------------------------------------------------
rent_total = 0.0
late_fee_total = 0.0
rent_by_prop: dict[str, float] = {p: 0.0 for p in PROPERTIES}

if rent_df is not None and not rent_df.empty:
    rdf = rent_df.copy()
    rdf["amount"] = pd.to_numeric(rdf["amount"], errors="coerce").fillna(0)
    rdf["late_fee"] = pd.to_numeric(rdf["late_fee"], errors="coerce").fillna(0)
    rdf["date_received"] = pd.to_datetime(rdf["date_received"], errors="coerce")
    rdf = rdf[rdf["date_received"].dt.year == year]

    if property_filter != "All Properties":
        rdf = rdf[rdf["property"] == property_filter]

    rent_total = rdf["amount"].sum()
    late_fee_total = rdf["late_fee"].sum()

    for _, row in rdf.iterrows():
        prop = row.get("property", "")
        if prop in rent_by_prop:
            rent_by_prop[prop] += float(row["amount"]) + float(row["late_fee"])

gross_income = rent_total + late_fee_total

# ---------------------------------------------------------------------------
# Process expenses
# ---------------------------------------------------------------------------
expenses_total = 0.0
cat_totals: dict[str, float] = {cat: 0.0 for cat in IRS_SCHEDULE_E_CATEGORIES}
exp_by_prop: dict[str, float] = {p: 0.0 for p in PROPERTIES}
capital_improvements: list[dict] = []
capital_total = 0.0

if exp_df is not None and not exp_df.empty:
    # default_year=year ensures undated backfill rows land in the year being viewed
    df = normalize_date_column(exp_df, "date", "timestamp", default_year=year)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df[df["date"].dt.year == year]

    if property_filter != "All Properties":
        df = df[df["property"] == property_filter]

    for _, row in df.iterrows():
        amt = float(row["amount"])
        cat = row.get("category", "Other")
        prop = row.get("property", "")

        # Capital improvements are NOT current-year expenses — they get depreciated.
        # Pull them out so Schedule E totals stay clean.
        if cat == CAPITAL_IMPROVEMENT_CATEGORY:
            capital_total += amt
            capital_improvements.append({
                "Date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "",
                "Property": prop,
                "Vendor": row.get("vendor", ""),
                "Description": row.get("description", "") or row.get("notes", ""),
                "Amount": amt,
            })
            continue

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
    mdf = normalize_date_column(mil_df, "date", "timestamp", default_year=year)
    mdf["deduction_amount"] = pd.to_numeric(mdf["deduction_amount"], errors="coerce").fillna(0)
    mdf["miles"] = pd.to_numeric(mdf["miles"], errors="coerce").fillna(0)
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

net_income = gross_income - grand_total

col1, col2, col3 = st.columns(3)
col1.metric("Gross Income (Sch E line 3)", format_currency(gross_income))
col2.metric("Total Deductions", format_currency(grand_total))
col3.metric("Net Income", format_currency(net_income), delta_color="normal")

col4, col5, col6 = st.columns(3)
col4.metric("Rent Received", format_currency(rent_total))
col5.metric("Expense Deductions", format_currency(expenses_total))
col6.metric("Mileage Deduction", f"{format_currency(mileage_deduction)}  \n({mileage_total_miles:,.1f} mi)")

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
        deductions = exp_by_prop[prop] + mil_by_prop[prop]
        income = rent_by_prop[prop]
        if deductions > 0 or income > 0:
            prop_rows.append({
                "Property": prop,
                "Income": format_currency(income),
                "Expenses": format_currency(exp_by_prop[prop]),
                "Mileage": format_currency(mil_by_prop[prop]),
                "Net": format_currency(income - deductions),
            })

    if prop_rows:
        st.dataframe(pd.DataFrame(prop_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No data to show.", icon="ℹ️")

# ---------------------------------------------------------------------------
# Capital Improvements — for CPA's depreciation schedule (Form 4562)
# ---------------------------------------------------------------------------
if capital_improvements:
    st.markdown("---")
    st.subheader("🏗️ Capital Improvements — For Depreciation Schedule")
    st.caption(
        "These items are capitalized and depreciated over 27.5 years on Form 4562. "
        "They are **NOT** included in Schedule E expense totals above. "
        "Hand this list to your CPA for the depreciation schedule."
    )
    cap_df = pd.DataFrame(capital_improvements).sort_values("Date", ascending=False)
    cap_display = cap_df.copy()
    cap_display["Amount"] = cap_display["Amount"].apply(format_currency)
    st.dataframe(cap_display, use_container_width=True, hide_index=True)
    st.metric(f"{year} Capital Improvements Total", format_currency(capital_total))

# ---------------------------------------------------------------------------
# Download CSV for accountant
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Export for Accountant")

if rows_sorted or gross_income > 0 or capital_total > 0 or (property_filter == "All Properties" and any(
    exp_by_prop[p] + mil_by_prop[p] > 0 for p in PROPERTIES
)):
    # Build a flat export with raw numbers
    export_rows = []
    if gross_income > 0:
        export_rows.append({
            "Tax Year": year,
            "Property": prop_label,
            "Section": "Income",
            "Schedule E Line": "Line 3 — Rents received",
            "Amount": round(rent_total, 2),
            "Note": "",
        })
        if late_fee_total > 0:
            export_rows.append({
                "Tax Year": year,
                "Property": prop_label,
                "Section": "Income",
                "Schedule E Line": "Line 3 — Late fees",
                "Amount": round(late_fee_total, 2),
                "Note": "Late fees count as rental income",
            })
    for cat, amt in cat_totals.items():
        if amt > 0:
            export_rows.append({
                "Tax Year": year,
                "Property": prop_label,
                "Section": "Expense",
                "Schedule E Line": cat,
                "Amount": round(amt, 2),
                "Note": f"Includes {mileage_total_miles:,.1f} mi @ IRS rate" if cat == "Auto and Travel" and mileage_deduction > 0 else "",
            })
    if capital_total > 0:
        export_rows.append({
            "Tax Year": year,
            "Property": prop_label,
            "Section": "Capital Improvement",
            "Schedule E Line": "Form 4562 — Depreciation (NOT a current-year expense)",
            "Amount": round(capital_total, 2),
            "Note": f"{len(capital_improvements)} item(s) — see detail rows below",
        })
        for item in capital_improvements:
            export_rows.append({
                "Tax Year": year,
                "Property": item["Property"],
                "Section": "Capital Improvement Detail",
                "Schedule E Line": f"{item['Date']} {item['Vendor']}",
                "Amount": round(item["Amount"], 2),
                "Note": item["Description"],
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
