import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import streamlit as st

from utils import ACCENT, chart_layout, date_filter, inject_global_css, load_all, render_drilldown

inject_global_css()

nav_l, nav_r = st.columns([6, 1])
with nav_l:
    st.markdown(
        "<a href='/' target='_self' style='font-family:\"DM Sans\",sans-serif;font-size:13px;"
        "color:#1B3A6B;text-decoration:none;font-weight:500;'>← Dashboard</a>",
        unsafe_allow_html=True,
    )
with nav_r:
    if st.button("↺ Reload", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Load data (always fresh — @st.cache_data handles perf) ───────────────────
df_all = load_all()
if df_all.empty:
    st.error("No data found. Return to the main page or drop CSVs into `data/`.")
    st.stop()

st.markdown("<div class='section-title'>Merchants</div>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
start, end, selected_card = date_filter(df_all, key="merch")
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

# ── Search ────────────────────────────────────────────────────────────────────
query = st.text_input("Search merchant", placeholder="e.g. Amazon, Delta, Whole Foods",
                      label_visibility="collapsed")

if query:
    df = df[df["Description"].str.contains(query, case=False, na=False)]
    if df.empty:
        st.warning(f'No transactions matching "{query}".')
        st.stop()

# ── Top merchants ─────────────────────────────────────────────────────────────
top_n = st.slider("Show top N merchants", 10, 50, 20)

merchants = (
    df.groupby("Description")["Amount"]
    .agg(["sum", "count", "mean"])
    .rename(columns={"sum": "Total", "count": "Visits", "mean": "Avg per Visit"})
    .sort_values("Total", ascending=False).head(top_n)
    .reset_index().rename(columns={"Description": "Merchant"})
)

# Summary metrics
def _stat(label, value):
    return (f"<div style='background:white;border-radius:10px;padding:16px 20px;"
            f"box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);'>"
            f"<div style='font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
            f"color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;'>{label}</div>"
            f"<div style='font-family:\"DM Mono\",monospace;font-size:22px;font-weight:500;color:#0F172A;'>{value}</div>"
            f"</div>")

m1, m2, m3 = st.columns(3)
m1.markdown(_stat("Total Spend",   f"${merchants['Total'].sum():,.2f}"),          unsafe_allow_html=True)
m2.markdown(_stat("Merchants",     str(len(merchants))),                           unsafe_allow_html=True)
m3.markdown(_stat("Avg per Visit", f"${merchants['Avg per Visit'].mean():,.2f}"), unsafe_allow_html=True)

# Bar chart
fig = px.bar(
    merchants, x="Total", y="Merchant", orientation="h",
    labels={"Total": "Spend ($)", "Merchant": ""},
    color_discrete_sequence=[ACCENT],
)
fig.update_layout(
    **chart_layout(height=max(380, top_n * 26)),
    yaxis={"categoryorder": "total ascending"},
    xaxis_tickprefix="$", xaxis_tickformat=",.0f",
)
fig.update_traces(
    hovertemplate="<b>%{y}</b><br>$%{x:,.2f}<extra></extra>"
)
st.markdown(
    "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;margin-bottom:4px;'>"
    "Click a bar to drill into that merchant's transactions.</div>",
    unsafe_allow_html=True,
)
merch_chart_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="merch_bar")

# ── Merchant detail table ──────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Detail</div>", unsafe_allow_html=True)
st.markdown(
    "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;margin-bottom:6px;'>"
    "Click a row to drill into that merchant's transactions.</div>",
    unsafe_allow_html=True,
)

merch_table_event = st.dataframe(
    merchants[["Merchant", "Total", "Visits", "Avg per Visit"]],
    on_select="rerun",
    selection_mode="single-row",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Total":         st.column_config.NumberColumn("Total",       format="$%.2f"),
        "Avg per Visit": st.column_config.NumberColumn("Avg / Visit", format="$%.2f"),
        "Visits":        st.column_config.NumberColumn("Visits"),
    },
    key="merch_table",
)

# Table row takes priority over chart bar
selected_merch = None
if merch_table_event.selection["rows"]:
    selected_merch = merchants.iloc[merch_table_event.selection["rows"][0]]["Merchant"]
elif merch_chart_event.selection["points"]:
    selected_merch = merch_chart_event.selection["points"][0].get("y")

if selected_merch:
    df_merch_drill = df[df["Description"] == selected_merch].sort_values("Amount", ascending=False)
    render_drilldown(df_merch_drill, f"{selected_merch} — {len(df_merch_drill)} transactions")
