import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import streamlit as st

from utils import CAT_COLORS, chart_layout, date_filter, inject_global_css, load_all, render_nav_bar, render_stat_card

inject_global_css()
render_nav_bar()

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
max_amount  = int(df["Amount"].quantile(0.99))
default_val = max(50, int(df["Amount"].quantile(0.90) / 50) * 50)  # round to nearest $50

threshold = st.slider(
    "Minimum transaction amount",
    min_value=50,
    max_value=max(max_amount, 100),
    value=min(default_val, max_amount),
    step=50,
    format="$%d",
)
large = (
    df[df["Amount"] >= threshold]
    .sort_values("Amount", ascending=False)
    .reset_index(drop=True)
)

c1, c2, c3 = st.columns(3)
c1.markdown(render_stat_card("Min Threshold",        f"${threshold:,.0f}"),             unsafe_allow_html=True)
c2.markdown(render_stat_card("Flagged Transactions", f"{len(large):,}"),                unsafe_allow_html=True)
c3.markdown(render_stat_card("Total Flagged Spend",  f"${large['Amount'].sum():,.0f}"), unsafe_allow_html=True)

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
