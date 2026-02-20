import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import streamlit as st

from utils import CAT_COLORS, chart_layout, date_filter, inject_global_css, load_all

inject_global_css()

st.markdown(
    "<a href='/' target='_self' style='font-family:\"DM Sans\",sans-serif;font-size:13px;"
    "color:#1B3A6B;text-decoration:none;font-weight:500;'>← Dashboard</a>",
    unsafe_allow_html=True,
)

# ── Load data ─────────────────────────────────────────────────────────────────
if "df_all" in st.session_state and not st.session_state["df_all"].empty:
    df_all = st.session_state["df_all"]
else:
    df_all = load_all()
    if df_all.empty:
        st.error("No data found. Return to the main page or drop CSVs into `data/`.")
        st.stop()

st.markdown("<div class='section-title'>Large Transactions</div>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
start, end, selected_card = date_filter(df_all, key="large")
st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_all.copy()
df = df[df["RecordType"] == "expense"]
df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]
if selected_card != "All cards":
    df = df[df["Card"] == selected_card]
if df.empty:
    st.warning("No transactions match the current filters.")
    st.stop()

# ── Large Transactions ────────────────────────────────────────────────────────
percentile = st.slider("Flag transactions in the top X% by amount", 1, 25, 5)
threshold  = df["Amount"].quantile(1 - percentile / 100)
large = (
    df[df["Amount"] >= threshold]
    .sort_values("Amount", ascending=False)
    .reset_index(drop=True)
)

c1, c2, c3 = st.columns(3)
c1.metric("Threshold",            f"${threshold:,.2f}")
c2.metric("Flagged Transactions", f"{len(large):,}")
c3.metric("Total Flagged Spend",  f"${large['Amount'].sum():,.2f}")

fig7 = px.scatter(
    large, x="Date", y="Amount", color="Category",
    hover_data={"Description": True, "Card": True},
    labels={"Amount": "Amount ($)"},
    color_discrete_sequence=CAT_COLORS,
)
fig7.update_layout(**chart_layout(), yaxis_tickprefix="$", yaxis_tickformat=",.0f")
fig7.update_traces(marker=dict(size=10, opacity=0.8))
st.plotly_chart(fig7, use_container_width=True)

st.dataframe(
    large[["Date", "Description", "Category", "Amount", "Card"]]
    .style.format({
        "Amount": "${:,.2f}",
        "Date": lambda d: d.strftime("%Y-%m-%d"),
    }),
    use_container_width=True, hide_index=True,
)
