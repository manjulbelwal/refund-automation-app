import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Refund Intelligence App", layout="wide")

st.title("📊 Refund Intelligence Dashboard")

# ==============================
# FILE UPLOAD
# ==============================
st.sidebar.header("Upload Files")
master_file = st.sidebar.file_uploader("Upload Master File", type=["xlsx"])
daily_file = st.sidebar.file_uploader("Upload Daily Refund File", type=["xlsx"])

# ==============================
# PROCESS MASTER FILE
# ==============================
if master_file:
    try:
        complaints = pd.read_excel(master_file, sheet_name="Complaints_Base")

        st.success("Master file loaded successfully!")

        # ==============================
        # COLUMN MAPPING
        # ==============================
        complaints["Product_Value"] = complaints.iloc[:, 12]   # Column M
        complaints["Final_Status"] = complaints.iloc[:, 22]    # Column W
        complaints["Mobile"] = complaints.iloc[:, 3]           # Column D
        complaints["Occurrence"] = complaints.iloc[:, 4]       # Column E
        complaints["GL"] = complaints.iloc[:, 26]              # Column AA
        complaints["Date"] = complaints.iloc[:, 16]            # Column Q (IMPORTANT FIX)

        complaints["Date"] = pd.to_datetime(complaints["Date"], errors='coerce')

        # Detect ASIN
        asin_col = [col for col in complaints.columns if "asin" in col.lower()]
        complaints["ASIN"] = complaints[asin_col[0]] if asin_col else "Unknown"

        # ==============================
        # CLEAN PRODUCT VALUE
        # ==============================
        complaints["Product_Value"] = (
            complaints["Product_Value"]
            .astype(str)
            .str.replace("₹", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )

        complaints["Product_Value"] = pd.to_numeric(
            complaints["Product_Value"], errors="coerce"
        ).fillna(0)

        # ==============================
        # STATUS LOGIC
        # ==============================
        refund_status = [
            "Closed(Refund Given)",
            "Closed(Refund Given-HI&BISS)",
            "Closed(Refund Given-BONKASO)"
        ]

        savings_status = [
            "Rejected",
            "Closed(No Response From CX)",
            "Closed(Issue Resolved)"
        ]

        complaints["Refund_Value"] = complaints.apply(
            lambda x: x["Product_Value"] if x["Final_Status"] in refund_status else 0,
            axis=1
        )

        complaints["Savings_Value"] = complaints.apply(
            lambda x: x["Product_Value"] if x["Final_Status"] in savings_status else 0,
            axis=1
        )

        # ==============================
        # FILTERS (NOW BASED ON COLUMN Q)
        # ==============================
        st.sidebar.header("Filters")

        min_date = complaints["Date"].min()
        max_date = complaints["Date"].max()

        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

        if len(date_range) == 2:
            complaints = complaints[
                (complaints["Date"] >= pd.to_datetime(date_range[0])) &
                (complaints["Date"] <= pd.to_datetime(date_range[1]))
            ]

        # ==============================
        # KPI METRICS
        # ==============================
        st.header("📌 Key Metrics")

        total_refund = complaints["Refund_Value"].sum()
        total_savings = complaints["Savings_Value"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Complaints", len(complaints))
        col2.metric("Total Refund (₹)", f"{total_refund:,.0f}")
        col3.metric("Total Savings (₹)", f"{total_savings:,.0f}")

        # ==============================
        # MONTHLY ANALYSIS
        # ==============================
        st.subheader("📈 Monthly Trend")

        complaints["Month"] = complaints["Date"].dt.to_period("M").astype(str)
        monthly = complaints.groupby("Month")[["Refund_Value", "Savings_Value"]].sum()
        st.line_chart(monthly)

        # ==============================
        # GL → ASIN BREAKDOWN (ENHANCED)
        # ==============================
        st.header("📊 GL → ASIN Breakdown")

        # Totals at top
        total_df = complaints.groupby("GL")[["Refund_Value", "Savings_Value"]].sum().reset_index()
        st.subheader("🔢 GL Level Totals")
        st.dataframe(total_df.sort_values(by="Refund_Value", ascending=False))

        st.subheader("📂 Expand for ASIN Level Details")

        for gl in complaints["GL"].dropna().unique():
            gl_data = complaints[complaints["GL"] == gl]

            gl_total_refund = gl_data["Refund_Value"].sum()
            gl_total_savings = gl_data["Savings_Value"].sum()

            with st.expander(f"GL: {gl} | Refund ₹{gl_total_refund:,.0f} | Savings ₹{gl_total_savings:,.0f}"):

                asin_group = gl_data.groupby("ASIN")[["Refund_Value", "Savings_Value"]].sum().reset_index()

                st.dataframe(asin_group.sort_values(by="Refund_Value", ascending=False))

        # ==============================
        # CUSTOMER INSIGHTS
        # ==============================
        st.header("👥 Customer Insights")

        customer_group = complaints.groupby("Mobile").agg({
            "Refund_Value": "sum",
            "Savings_Value": "sum",
            "Occurrence": "max"
        }).reset_index()

        st.dataframe(customer_group.sort_values(by="Refund_Value", ascending=False))

    except Exception as e:
        st.error(f"Error processing master file: {e}")

# ==============================
# DAILY VALIDATION
# ==============================
if daily_file:
    try:
        orders = pd.read_excel(daily_file, sheet_name="Order")

        st.header("🧪 Daily Refund Validation")
        st.write("Total Orders:", len(orders))

        # Missing Values
        missing = orders.isnull().sum()
        missing = missing[missing > 0]

        if not missing.empty:
            st.warning("Missing values found")
            st.dataframe(missing)
        else:
            st.success("No missing values")

        # Duplicate Orders
        order_col = [col for col in orders.columns if "order" in col.lower()]

        if order_col:
            duplicates = orders[orders.duplicated(subset=[order_col[0]], keep=False)]

            if not duplicates.empty:
                st.error("Duplicate Order IDs found")
                st.dataframe(duplicates)
            else:
                st.success("No duplicate orders")

    except Exception as e:
        st.error(f"Error processing daily file: {e}")
