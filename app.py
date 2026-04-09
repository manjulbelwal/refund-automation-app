import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Refund Automation App", layout="wide")

st.title("📊 Refund Automation Dashboard")

# ==============================
# FILE UPLOADS
# ==============================
st.sidebar.header("Upload Files")

master_file = st.sidebar.file_uploader("Upload Master File", type=["xlsx"])
daily_file = st.sidebar.file_uploader("Upload Daily Refund File", type=["xlsx"])

# ==============================
# LOAD MASTER DATA
# ==============================
if master_file:
    try:
        complaints = pd.read_excel(master_file, sheet_name="Complaints_Base")
        warranty = pd.read_excel(master_file, sheet_name="Warranty_Period")

        st.success("Master file loaded successfully!")

        # Convert date column (auto detect)
        date_col = None
        for col in complaints.columns:
            if "date" in col.lower():
                date_col = col
                complaints[col] = pd.to_datetime(complaints[col], errors='coerce')
                break

        # ==============================
        # DASHBOARD
        # ==============================
        st.header("📈 Dashboard")

        col1, col2, col3 = st.columns(3)

        total_refund = complaints.select_dtypes(include=['number']).sum().sum()
        total_records = len(complaints)

        col1.metric("Total Records", total_records)
        col2.metric("Total Numeric Value", round(total_refund, 2))

        if date_col:
            complaints['Month'] = complaints[date_col].dt.to_period('M').astype(str)

            monthly = complaints.groupby('Month').size().reset_index(name='Count')
            st.subheader("Monthly Trend")
            st.line_chart(monthly.set_index('Month'))

        # ASIN Level
        asin_col = [col for col in complaints.columns if "asin" in col.lower()]
        if asin_col:
            st.subheader("ASIN Level Stats")
            asin_stats = complaints.groupby(asin_col[0]).size().reset_index(name='Count')
            st.dataframe(asin_stats)

    except Exception as e:
        st.error(f"Error loading master file: {e}")

# ==============================
# DAILY FILE VALIDATION
# ==============================
if daily_file:
    try:
        orders = pd.read_excel(daily_file, sheet_name="Order")

        st.header("🧪 Daily Refund Validation")

        st.write("Total Orders in File:", len(orders))

        # ------------------------------
        # MISSING VALUES CHECK
        # ------------------------------
        st.subheader("Missing Values Check")

        missing = orders.isnull().sum()
        missing = missing[missing > 0]

        if not missing.empty:
            st.warning("Missing values found:")
            st.dataframe(missing)
        else:
            st.success("No missing values!")

        # ------------------------------
        # DUPLICATE ORDER ID CHECK
        # ------------------------------
        st.subheader("Duplicate Order ID Check")

        order_id_col = None
        for col in orders.columns:
            if "order" in col.lower():
                order_id_col = col
                break

        if order_id_col:
            duplicates = orders[orders.duplicated(subset=[order_id_col], keep=False)]

            if not duplicates.empty:
                st.error("Duplicate Order IDs found!")
                st.dataframe(duplicates)
            else:
                st.success("No duplicate Order IDs!")

        # ------------------------------
        # MISUSE CHECK (>3 refunds in 365 days)
        # ------------------------------
        st.subheader("Customer Misuse Check (>3 refunds in 365 days)")

        email_col = None
        for col in orders.columns:
            if "email" in col.lower():
                email_col = col
                break

        if master_file and email_col:
            complaints[email_col] = complaints[email_col].astype(str)

            last_365_days = complaints[
                complaints[date_col] >= (datetime.now() - timedelta(days=365))
            ]

            counts = last_365_days.groupby(email_col).size().reset_index(name='refund_count')

            misuse = counts[counts['refund_count'] > 3]

            if not misuse.empty:
                st.error("Potential misuse customers found!")
                st.dataframe(misuse)
            else:
                st.success("No misuse detected!")

    except Exception as e:
        st.error(f"Error processing daily file: {e}")
