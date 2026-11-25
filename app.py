import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io

st.set_page_config(page_title="Supplier Watch | Purchasing Analytics", layout="wide")

st.title("Supplier Watch: Supplier Performance & Risk Dashboard")
st.caption("Tracking On-Time Delivery (OTD), Defect Rate (PPM), Cost Trends & Weighted Supplier Risk")

# Connect to Neon PostgreSQL
conn = st.connection("postgresql", type="sql")

# 1. SQL Query for Supplier-Level Aggregated KPIs
supplier_query = """
SELECT 
    s.supplier_id,
    s.supplier_name,
    s.category,
    s.region,
    COUNT(p.po_id) AS total_orders,
    ROUND(AVG(p.is_on_time) * 100.0, 2) AS otd_pct,
    SUM(p.units_received) AS total_units,
    SUM(p.defective_units) AS total_defects,
    ROUND((SUM(p.defective_units)::numeric / NULLIF(SUM(p.units_received), 0)) * 1000000, 0) AS ppm,
    ROUND((AVG((p.unit_price - p.baseline_unit_price) / p.baseline_unit_price) * 100.0)::numeric, 2) AS cost_variance_pct,
    ROUND(SUM(p.total_spend)::numeric, 2) AS total_spend
FROM suppliers s
JOIN purchase_orders p ON s.supplier_id = p.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.category, s.region
ORDER BY total_spend DESC;
"""

# 2. SQL Query for Monthly Cost & Delivery Trends
trend_query = """
SELECT 
    TO_CHAR(p.order_date, 'YYYY-MM') AS order_month,
    s.category,
    ROUND(AVG(p.unit_price)::numeric, 2) AS avg_unit_price,
    ROUND(AVG(p.is_on_time) * 100.0, 2) AS monthly_otd,
    ROUND((SUM(p.defective_units)::numeric / NULLIF(SUM(p.units_received), 0)) * 1000000, 0) AS monthly_ppm
FROM purchase_orders p
JOIN suppliers s ON p.supplier_id = s.supplier_id
GROUP BY order_month, s.category
ORDER BY order_month;
"""

df_sup = conn.query(supplier_query, ttl="10m")
df_trend = conn.query(trend_query, ttl="10m")

for col in ["otd_pct", "ppm", "cost_variance_pct", "total_spend"]:
    df_sup[col] = pd.to_numeric(df_sup[col])

# 3. Weighted Risk Score Formula (0 - 100)
# 40% Delivery Risk + 35% Quality Risk (PPM) + 25% Cost Escalation Risk
delivery_risk = (100 - df_sup["otd_pct"]).clip(0, 100)
quality_risk = ((df_sup["ppm"] / 10000.0) * 100).clip(0, 100)
cost_risk = (df_sup["cost_variance_pct"].clip(lower=0) * 10).clip(0, 100)

df_sup["risk_score"] = (0.40 * delivery_risk + 0.35 * quality_risk + 0.25 * cost_risk).round(1)

def classify_risk(score):
    if score >= 50:
        return "Critical"
    elif score >= 30:
        return "High Risk"
    return "Low / Moderate"

def suggest_mitigation(row):
    actions = []
    if row["ppm"] > 4000:
        actions.append("Initiate 8D root-cause audit & PPAP re-validation")
    if row["otd_pct"] < 85:
        actions.append("Enforce 2-week safety stock & dual-source backup")
    if row["cost_variance_pct"] > 3.5:
        actions.append("Conduct Should-Cost breakdown & commercial renegotiation")
    if not actions:
        actions.append("Maintain quarterly QBR & standard scorecard monitoring")
    return " | ".join(actions)

df_sup["risk_tier"] = df_sup["risk_score"].apply(classify_risk)
df_sup["mitigation_action"] = df_sup.apply(suggest_mitigation, axis=1)

# Sidebar Filters
st.sidebar.header("Filter Purchasing Data")
selected_cats = st.sidebar.multiselect("Category", df_sup["category"].unique(), default=df_sup["category"].unique())
selected_regions = st.sidebar.multiselect("Region", df_sup["region"].unique(), default=df_sup["region"].unique())
selected_tiers = st.sidebar.multiselect("Risk Tier", ["Critical", "High Risk", "Low / Moderate"], default=["Critical", "High Risk", "Low / Moderate"])

filtered_df = df_sup[
    (df_sup["category"].isin(selected_cats)) &
    (df_sup["region"].isin(selected_regions)) &
    (df_sup["risk_tier"].isin(selected_tiers))
]

# Top KPI Cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg On-Time Delivery", f"{filtered_df['otd_pct'].mean():.1f}%")
c2.metric("Avg Defect Rate (PPM)", f"{filtered_df['ppm'].mean():,.0f}")
c3.metric("Total Tracked Spend", f"₹{filtered_df['total_spend'].sum():,.0f}")
critical_count = len(filtered_df[filtered_df["risk_tier"].isin(["Critical", "High Risk"])])
c4.metric("Critical / High-Risk Suppliers", f"{critical_count} / {len(filtered_df)}")

st.divider()

# Charts Row
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Supplier Risk Matrix (OTD % vs. Defect PPM)")
    fig_scatter = px.scatter(
        filtered_df,
        x="otd_pct",
        y="ppm",
        size="total_spend",
        color="risk_tier",
        hover_name="supplier_name",
        color_discrete_map={"Critical": "#d62728", "High Risk": "#ff7f0e", "Low / Moderate": "#2ca02c"},
        labels={"otd_pct": "On-Time Delivery (%)", "ppm": "Defect Rate (PPM)"}
    )
    fig_scatter.add_vline(x=85, line_dash="dash", line_color="gray", annotation_text="OTD Target (85%)")
    fig_scatter.add_hline(y=4000, line_dash="dash", line_color="gray", annotation_text="PPM Threshold (4,000)")
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_right:
    st.subheader("Monthly Unit Cost Trend by Category")
    trend_filtered = df_trend[df_trend["category"].isin(selected_cats)]
    fig_line = px.line(
        trend_filtered,
        x="order_month",
        y="avg_unit_price",
        color="category",
        markers=True,
        labels={"order_month": "Month", "avg_unit_price": "Avg Unit Price (₹)"}
    )
    st.plotly_chart(fig_line, use_container_width=True)

# Actionable Risk & Mitigation Table
st.subheader("Supplier Risk Scorecard & Recommended Mitigation Actions")
display_cols = [
    "supplier_id", "supplier_name", "category", "region",
    "otd_pct", "ppm", "cost_variance_pct", "risk_score", "risk_tier", "mitigation_action"
]
st.dataframe(filtered_df[display_cols].sort_values(by="risk_score", ascending=False), use_container_width=True)

# Excel Export Button
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    filtered_df.to_excel(writer, index=False, sheet_name="Supplier_Risk_Scorecard")

st.download_button(
    label="Download Risk Scorecard (Excel)",
    data=buffer.getvalue(),
    file_name="Supplier_Watch_Scorecard.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
