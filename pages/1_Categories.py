import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import ACCENT, CAT_COLORS, chart_layout, date_filter, inject_global_css, load_all

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

st.markdown("<div class='section-title'>Categories</div>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
start, end, selected_card = date_filter(df_all, key="cat")
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

# ── Category aggregation ──────────────────────────────────────────────────────
other_threshold = st.slider("Group categories below this % into 'Other'", 0, 10, 1)

cat_full = (
    df.groupby("Category")["Amount"]
    .agg(["sum", "count"])
    .rename(columns={"sum": "Total", "count": "Transactions"})
    .sort_values("Total", ascending=False)
    .reset_index()
)
total_spend = cat_full["Total"].sum()
cat_full["% of Spend"] = (cat_full["Total"] / total_spend * 100).round(1)
cat_full["Avg per Txn"] = (cat_full["Total"] / cat_full["Transactions"]).round(2)

small = cat_full[cat_full["% of Spend"] < other_threshold]
if not small.empty and other_threshold > 0:
    other_row = pd.DataFrame([{
        "Category": "Other",
        "Total": small["Total"].sum(),
        "Transactions": small["Transactions"].sum(),
        "% of Spend": round(small["% of Spend"].sum(), 1),
        "Avg per Txn": round(small["Total"].sum() / small["Transactions"].sum(), 2),
    }])
    cat_full = (
        pd.concat([cat_full[cat_full["% of Spend"] >= other_threshold], other_row],
                  ignore_index=True)
        .sort_values("Total", ascending=False)
        .reset_index(drop=True)
    )

# ── Summary metrics ────────────────────────────────────────────────────────────
def _stat(label, value):
    return (f"<div style='background:white;border-radius:10px;padding:16px 20px;"
            f"box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);'>"
            f"<div style='font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
            f"color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;'>{label}</div>"
            f"<div style='font-family:\"DM Mono\",monospace;font-size:22px;font-weight:500;color:#0F172A;'>{value}</div>"
            f"</div>")

m1, m2, m3 = st.columns(3)
m1.markdown(_stat("Total Spend",  f"${total_spend:,.2f}"),               unsafe_allow_html=True)
m2.markdown(_stat("Categories",   str(len(cat_full))),                   unsafe_allow_html=True)
m3.markdown(_stat("Avg per Txn",  f"${cat_full['Avg per Txn'].mean():,.2f}"), unsafe_allow_html=True)

# ── Horizontal bar chart ───────────────────────────────────────────────────────
fig = px.bar(
    cat_full, x="Total", y="Category", orientation="h",
    labels={"Total": "Spend ($)", "Category": ""},
    color="Category",
    color_discrete_sequence=CAT_COLORS,
)
fig.update_layout(
    **chart_layout(),
    yaxis={"categoryorder": "total ascending"},
    xaxis_tickprefix="$", xaxis_tickformat=",.0f",
    showlegend=False,
)
fig.update_traces(
    hovertemplate="<b>%{y}</b><br>$%{x:,.2f}<extra></extra>"
)
st.plotly_chart(fig, use_container_width=True)

# ── Clean summary table ────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Breakdown</div>", unsafe_allow_html=True)

rows_html = ""
for i, row in cat_full.iterrows():
    color = CAT_COLORS[i % len(CAT_COLORS)]
    bar_width = row["% of Spend"] * 2  # scale for visual
    rows_html += f"""
<div style="display:grid;grid-template-columns:16px 1fr 60px 100px 70px 70px;
     align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #F1F5F9;">
  <div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;"></div>
  <div>
    <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:#0F172A;font-weight:500;">{row['Category']}</div>
    <div style="background:{color}22;height:4px;border-radius:2px;margin-top:5px;width:{min(bar_width,100):.0f}%;"></div>
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#475569;text-align:right;">{row['% of Spend']:.1f}%</div>
  <div style="font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Total']:,.2f}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#475569;text-align:right;">{int(row['Transactions'])} txns</div>
  <div style="font-family:'DM Mono',monospace;font-size:13px;color:#475569;text-align:right;">${row['Avg per Txn']:,.2f} avg</div>
</div>"""

st.markdown(
    f"<div style='background:white;border-radius:12px;padding:4px 20px 12px;"
    f"box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);"
    f"margin-bottom:24px;'>{rows_html}</div>",
    unsafe_allow_html=True,
)
