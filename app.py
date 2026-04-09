import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Refund Intelligence App", layout="wide")

st.title("📊 Refund Intelligence Dashboard")

# ==============================
# UPLOAD FILES
# ==============================
st.sidebar.header("Upload Files")
master_file = st.sidebar.file_uploader("Upload Master File", type=["xlsx"])
daily_file = st.sidebar.file_uploader("Upload Daily Refund File", type=["xlsx"])

# ==============================
# LOAD MASTER FILE
# ==============================
if master_file:
    complaints = pd.read_excel(master_file, sheet_name="Complaints_Base")

    st.success("Master file loaded successfully!")

    # ==============================
    # COLUMN MAPPING (BASED ON YOUR INPUT)
    # ==============================
    complaints["Product_Value"] = complaints.iloc[:, 12]   # Column M
    complaints["Final_Status"] = complaints.iloc[:, 22]    # Column W
    complaints["Mobile"] = complaints.iloc[:, 3]           # Column D
    complaints["Occurrence"] = complaints.iloc[:, 4]       # Column E
    complaints["GL"] = complaints.iloc[:, 26]              # Column AA

    # Detect ASIN column
    asin_col = [col for col in complaints.columns if "asin" in col.lower()]
    if asin_col:
        complaints["ASIN"] = complaints[asin_col[0]]

    # Detect date column
    date_col = None
    for col in complaints.columns:
        if "date" in col.lower():
            date_col = col
            complaints[col] = pd.to_datetime(complaints[col], errors='coerce')
            break

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
    # FILTERS
    # ==============================
    st.sidebar.header("Filters")

    if date_col:
        min_date = complaints[date_col].min()
        max_date = complaints[date_col].max()

        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

        if len(date_range) == 2:
            complaints = complaints[
                (complaints[date_col] >= pd.to_datetime(date_range[0])) &
                (complaints[date_col] <= pd.to_datetime(date_range[1]))
            ]

    # ==============================
    # KPI METRICS
    # ==============================
    st.header("📌 Key Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Complaints", len(complaints))
    col2.metric("Total Refund (₹)", int(complaints["Refund_Value"].sum()))
    col3.metric("Total Savings (₹)", int(complaints["Savings_Value"].sum()))

    # ==============================
    # LLM STYLE QUESTIONS
    # ==============================
    st.subheader("💡 Ask Business Questions")

    question = st.selectbox(
        "Select a question",
        [
            "Total Refund This Year",
            "Total Savings This Year",
            "Refund vs Savings (Monthly)",
        ]
    )

    if question == "Total Refund This Year":
        st.success(f"₹ {int(complaints['Refund_Value'].sum())}")

    elif question == "Total Savings This Year":
        st.success(f"₹ {int(complaints['Savings_Value'].sum())}")

    elif question == "Refund vs Savings (Monthly)":
        if date_col:
            complaints["Month"] = complaints[date_col].dt.to_period("M").astype(str)
            monthly = complaints.groupby("Month")[["Refund_Value", "Savings_Value"]].sum()
            st.line_chart(monthly)

    # ==============================
    # GL → ASIN DASHBOARD
    # ==============================
    st.header("📊 GL → ASIN Breakdown")

    gl_group = complaints.groupby(["GL", "ASIN"])[["Refund_Value", "Savings_Value"]].sum().reset_index()
    st.dataframe(gl_group)

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

# ==============================
# DAILY VALIDATION
# ==============================
if daily_file:
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

    # Duplicate Check
    order_col = [col for col in orders.columns if "order" in col.lower()]
    if order_col:
        duplicates = orders[orders.duplicated(subset=[order_col[0]], keep=False)]

        if not duplicates.empty:
            st.error("Duplicate Order IDs found")
            st.dataframe(duplicates)
        else:
            st.success("No duplicate orders")
