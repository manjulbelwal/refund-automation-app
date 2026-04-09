import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="Refund Intelligence AI", layout="wide")

st.title("🚀 Refund Intelligence AI Dashboard")

# ==============================
# FILE UPLOAD
# ==============================
st.sidebar.header("Upload Files")
master_file = st.sidebar.file_uploader("Upload Master File", type=["xlsx"])

# ==============================
# PROCESS MASTER FILE
# ==============================
if master_file:
    try:
        df = pd.read_excel(master_file, sheet_name="Complaints_Base")

        # COLUMN MAPPING
        df["Product_Value"] = df.iloc[:, 12]
        df["Final_Status"] = df.iloc[:, 22]
        df["Mobile"] = df.iloc[:, 3]
        df["Occurrence"] = df.iloc[:, 4]
        df["GL"] = df.iloc[:, 26]
        df["Date"] = pd.to_datetime(df.iloc[:, 16], errors='coerce')

        asin_col = [col for col in df.columns if "asin" in col.lower()]
        df["ASIN"] = df[asin_col[0]] if asin_col else "Unknown"

        # CLEAN ₹
        df["Product_Value"] = (
            df["Product_Value"].astype(str)
            .str.replace("₹", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        df["Product_Value"] = pd.to_numeric(df["Product_Value"], errors="coerce").fillna(0)

        # STATUS LOGIC
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

        df["Refund_Value"] = df.apply(
            lambda x: x["Product_Value"] if x["Final_Status"] in refund_status else 0, axis=1
        )

        df["Savings_Value"] = df.apply(
            lambda x: x["Product_Value"] if x["Final_Status"] in savings_status else 0, axis=1
        )

        # ==============================
        # KPI
        # ==============================
        st.header("📌 KPIs")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Complaints", len(df))
        col2.metric("Total Refund ₹", f"{df['Refund_Value'].sum():,.0f}")
        col3.metric("Total Savings ₹", f"{df['Savings_Value'].sum():,.0f}")

        # ==============================
        # POWER BI GRID
        # ==============================
        st.header("📊 GL → ASIN (Power BI Style)")

        grouped = df.groupby(["GL", "ASIN"])[["Refund_Value", "Savings_Value"]].sum().reset_index()

        gb = GridOptionsBuilder.from_dataframe(grouped)
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True)
        gb.configure_grid_options(
            groupDisplayType="multipleColumns",
            groupDefaultExpanded=0
        )

        gridOptions = gb.build()

        AgGrid(
            grouped,
            gridOptions=gridOptions,
            enable_enterprise_modules=True,
            fit_columns_on_grid_load=True
        )

        # ==============================
        # CUSTOMER INSIGHTS
        # ==============================
        st.header("👥 Customer Insights")

        customer = df.groupby("Mobile").agg({
            "Refund_Value": "sum",
            "Savings_Value": "sum",
            "Occurrence": "max"
        }).reset_index()

        st.dataframe(customer.sort_values(by="Refund_Value", ascending=False))

        # ==============================
        # FRAUD DETECTION
        # ==============================
        st.header("🚨 Fraud Detection")

        fraud = customer[
            (customer["Refund_Value"] > 10000) |
            (customer["Occurrence"] > 3)
        ]

        if not fraud.empty:
            st.error("Fraudulent Customers Detected")
            st.dataframe(fraud)
        else:
            st.success("No Fraud Detected")

        # ==============================
        # DOWNLOAD REPORTS
        # ==============================
        st.header("📥 Download Reports")

        st.download_button(
            "Download GL Summary",
            grouped.to_csv(index=False),
            "gl_summary.csv"
        )

        st.download_button(
            "Download Customer Insights",
            customer.to_csv(index=False),
            "customer_insights.csv"
        )

        st.download_button(
            "Download Fraud Report",
            fraud.to_csv(index=False),
            "fraud_report.csv"
        )

        # ==============================
        # CHATBOT
        # ==============================
        st.header("🤖 Ask Questions")

        query = st.text_input("Ask something (e.g. total refund, top GL, fraud customers)")

        if query:
            q = query.lower()

            if "refund" in q:
                st.success(f"Total Refund ₹ {df['Refund_Value'].sum():,.0f}")

            elif "saving" in q:
                st.success(f"Total Savings ₹ {df['Savings_Value'].sum():,.0f}")

            elif "top gl" in q:
                top_gl = grouped.sort_values(by="Refund_Value", ascending=False).head(5)
                st.dataframe(top_gl)

            elif "fraud" in q:
                st.dataframe(fraud)

            else:
                st.warning("Try: refund / savings / top GL / fraud")

    except Exception as e:
        st.error(f"Error: {e}")
