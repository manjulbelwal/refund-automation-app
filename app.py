import streamlit as st
import pandas as pd

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
        complaints["Product_Value"] = complaints.iloc[:, 12]
        complaints["Final_Status"] = complaints.iloc[:, 22]
        complaints["Mobile"] = complaints.iloc[:, 3]
        complaints["Occurrence"] = complaints.iloc[:, 4]
        complaints["GL"] = complaints.iloc[:, 26]
        complaints["Date"] = complaints.iloc[:, 16]

        complaints["Date"] = pd.to_datetime(complaints["Date"], errors='coerce')

        # Detect ASIN column
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

        complaints["Refund_Value"] = complaints["Refund_Value"].fillna(0)
        complaints["Savings_Value"] = complaints["Savings_Value"].fillna(0)

        # ==============================
        # FILTERS
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
        # MONTHLY TREND
        # ==============================
        st.subheader("📈 Monthly Trend")

        complaints["Month"] = complaints["Date"].dt.to_period("M").astype(str)
        monthly = complaints.groupby("Month")[["Refund_Value", "Savings_Value"]].sum()

        st.line_chart(monthly)

        # ==============================
        # GL → ASIN DRILLDOWN
        # ==============================
        st.header("📊 GL → ASIN Drilldown")

        gl_summary = complaints.groupby("GL")[["Refund_Value", "Savings_Value"]].sum().reset_index()
        gl_summary = gl_summary.sort_values(by="Refund_Value", ascending=False)

        gl_summary["Refund_Display"] = gl_summary["Refund_Value"].apply(lambda x: f"₹{x:,.0f}")
        gl_summary["Savings_Display"] = gl_summary["Savings_Value"].apply(lambda x: f"₹{x:,.0f}")

        st.subheader("🔢 GL Summary")

        display_df = gl_summary[["GL", "Refund_Display", "Savings_Display"]].rename(columns={
            "GL": "GL Category",
            "Refund_Display": "Refund ₹",
            "Savings_Display": "Savings ₹"
        })

        st.dataframe(display_df, use_container_width=True)

        st.subheader("➕ Click below to expand GL → ASIN")

        for _, row in gl_summary.iterrows():

            gl = row["GL"]
            gl_refund = row["Refund_Value"]
            gl_savings = row["Savings_Value"]

            with st.expander(f"➕ GL: {gl} | Refund ₹{gl_refund:,.0f} | Savings ₹{gl_savings:,.0f}"):

                gl_data = complaints[complaints["GL"] == gl]

                asin_group = gl_data.groupby("ASIN")[["Refund_Value", "Savings_Value"]].sum().reset_index()
                asin_group = asin_group.sort_values(by="Refund_Value", ascending=False)

                asin_group["Refund ₹"] = asin_group["Refund_Value"].apply(lambda x: f"₹{x:,.0f}")
                asin_group["Savings ₹"] = asin_group["Savings_Value"].apply(lambda x: f"₹{x:,.0f}")

                st.dataframe(
                    asin_group[["ASIN", "Refund ₹", "Savings ₹"]],
                    use_container_width=True
                )

        # ==============================
        # CUSTOMER INSIGHTS
        # ==============================
        st.header("👥 Customer Insights")

        customer_group = complaints.groupby("Mobile").agg({
            "Refund_Value": "sum",
            "Savings_Value": "sum",
            "Occurrence": "max"
        }).reset_index()

        st.dataframe(
            customer_group.sort_values(by="Refund_Value", ascending=False),
            use_container_width=True
        )

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

        missing = orders.isnull().sum()
        missing = missing[missing > 0]

        if not missing.empty:
            st.warning("Missing values found")
            st.dataframe(missing)
        else:
            st.success("No missing values")

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
