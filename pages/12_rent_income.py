"""
pages/12_rent_income.py — Rent Income

Log rent payments by property/tenant. This feeds Schedule E line 3 (Rents received).
"""

import datetime
import pandas as pd
import streamlit as st

from utils.cache import safe_get_rent_income, safe_get_tenants, show_fetch_error
from utils.formatting import format_currency
from sheets.rent_income import add_rent_payment
from config import PROPERTIES, PAYMENT_METHODS

st.set_page_config(page_title="Rent Income", page_icon="💰", layout="centered")
st.title("💰 Rent Income")
st.caption("Log rent payments — feeds Schedule E line 3 (Rents received).")

# ---------------------------------------------------------------------------
# Tenant lookup helper — pull tenant name from latest Tenants record per property
# ---------------------------------------------------------------------------
tenants_df, _ = safe_get_tenants()


def _latest_tenant_for(prop: str) -> str:
    if tenants_df is None or tenants_df.empty:
        return ""
    sub = tenants_df[tenants_df["property"] == prop].copy()
    if sub.empty:
        return ""
    sub["entry_date"] = pd.to_datetime(sub["entry_date"], errors="coerce")
    sub = sub.sort_values("entry_date", ascending=False)
    name = sub.iloc[0].get("tenant_name", "")
    return str(name) if name else ""


# ---------------------------------------------------------------------------
# Log a payment
# ---------------------------------------------------------------------------
with st.form("rent_form", clear_on_submit=True):
    st.subheader("Log Rent Payment")

    prop = st.selectbox("Property *", PROPERTIES)
    suggested_tenant = _latest_tenant_for(prop)
    tenant = st.text_input("Tenant Name *", value=suggested_tenant)

    col1, col2 = st.columns(2)
    with col1:
        date_received = st.date_input("Date Received *", value=datetime.date.today())
    with col2:
        payment_method = st.selectbox("Payment Method", [""] + PAYMENT_METHODS)

    col3, col4 = st.columns(2)
    with col3:
        amount = st.number_input("Rent Amount ($) *", min_value=0.0, step=25.0, format="%.2f")
    with col4:
        late_fee = st.number_input("Late Fee ($)", min_value=0.0, step=5.0, format="%.2f")

    today = datetime.date.today()
    first_of_month = today.replace(day=1)
    next_month_first = (first_of_month + datetime.timedelta(days=32)).replace(day=1)
    last_of_month = next_month_first - datetime.timedelta(days=1)

    col5, col6 = st.columns(2)
    with col5:
        period_start = st.date_input("Period Start", value=first_of_month)
    with col6:
        period_end = st.date_input("Period End", value=last_of_month)

    notes = st.text_area("Notes", height=80, placeholder="Partial payment, prorated, security deposit applied, etc.")

    submitted = st.form_submit_button("Save Payment", use_container_width=True)
    if submitted:
        errors = []
        if not tenant.strip():
            errors.append("Tenant Name is required.")
        if amount <= 0:
            errors.append("Rent Amount must be greater than $0.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                add_rent_payment(
                    property=prop,
                    tenant_name=tenant.strip(),
                    date_received=date_received.isoformat(),
                    amount=amount,
                    late_fee=late_fee,
                    period_start=period_start.isoformat(),
                    period_end=period_end.isoformat(),
                    payment_method=payment_method,
                    notes=notes.strip(),
                )
                total_logged = amount + late_fee
                st.success(f"Logged {format_currency(total_logged)} for {tenant.strip()} ({prop})")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")

# ---------------------------------------------------------------------------
# History + summary
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Payment History")

df, err = safe_get_rent_income()
show_fetch_error(err)

if df is None or df.empty:
    st.info("No rent payments logged yet.", icon="ℹ️")
    st.stop()

# Filters
col1, col2 = st.columns(2)
with col1:
    prop_f = st.selectbox("Property", ["All"] + PROPERTIES, key="rent_prop")
with col2:
    current_year = datetime.date.today().year
    year_f = st.selectbox("Year", ["All"] + list(range(current_year, current_year - 6, -1)), key="rent_year")

filtered = df.copy()
filtered["amount"] = pd.to_numeric(filtered["amount"], errors="coerce").fillna(0)
filtered["late_fee"] = pd.to_numeric(filtered["late_fee"], errors="coerce").fillna(0)
filtered["date_received"] = pd.to_datetime(filtered["date_received"], errors="coerce")

if prop_f != "All":
    filtered = filtered[filtered["property"] == prop_f]
if year_f != "All":
    filtered = filtered[filtered["date_received"].dt.year == year_f]

# Summary metrics
total_rent = filtered["amount"].sum()
total_late = filtered["late_fee"].sum()
gross_income = total_rent + total_late

col_a, col_b, col_c = st.columns(3)
col_a.metric("Rent Received", format_currency(total_rent))
col_b.metric("Late Fees", format_currency(total_late))
col_c.metric("Gross Income (Schedule E line 3)", format_currency(gross_income))

# Per-property breakdown when "All" is selected
if prop_f == "All" and not filtered.empty:
    st.markdown("##### By Property")
    by_prop = filtered.groupby("property").agg(
        rent=("amount", "sum"),
        late=("late_fee", "sum"),
    ).reset_index()
    by_prop["Total"] = by_prop["rent"] + by_prop["late"]
    by_prop.columns = ["Property", "Rent", "Late Fees", "Total"]
    for col in ["Rent", "Late Fees", "Total"]:
        by_prop[col] = by_prop[col].apply(format_currency)
    st.dataframe(by_prop, use_container_width=True, hide_index=True)

# Detail table
st.markdown("##### Payments")
if filtered.empty:
    st.info("No payments match those filters.", icon="ℹ️")
else:
    display = filtered.sort_values("date_received", ascending=False).copy()
    display["date_received"] = display["date_received"].dt.strftime("%Y-%m-%d")
    display = display[["date_received", "property", "tenant_name", "amount", "late_fee", "payment_method", "notes"]]
    display.columns = ["Received", "Property", "Tenant", "Rent", "Late Fee", "Method", "Notes"]
    display["Rent"] = display["Rent"].apply(format_currency)
    display["Late Fee"] = display["Late Fee"].apply(lambda x: format_currency(x) if x else "")
    st.dataframe(display, use_container_width=True, hide_index=True)
