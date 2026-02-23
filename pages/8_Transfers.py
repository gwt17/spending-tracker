import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go
import streamlit as st

from utils import ACCENT, date_filter, format_year_month, inject_global_css, load_all, render_nav_bar, render_stat_card

inject_global_css()
render_nav_bar()

# ── Load data ─────────────────────────────────────────────────────────────────
df_all = load_all()
if df_all.empty:
    st.error("No data found. Return to the main page or drop CSVs into `data/`.")
    st.stop()

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1B3A6B 0%, #2563EB 100%);
    border-radius: 10px;
    padding: 14px 24px;
    margin-bottom: 16px;
">
    <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:white;letter-spacing:-0.02em;">
        Transfer Activity
    </div>
</div>
""", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
start, end, selected_card = date_filter(df_all, key="tfr", default_preset="Last 12 months")
st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_all.copy()
if selected_card != "All cards":
    df = df[df["Card"] == selected_card]
df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]

df_tfr    = df[df["RecordType"] == "transfer"].copy()
df_exp    = df[df["RecordType"] == "expense"].copy()
df_income = df[df["RecordType"] == "income"].copy()
has_income = not df_income.empty

if df_tfr.empty:
    st.info(
        "No transfers found in the selected range. "
        "Transfers are checking account transactions matching keywords like Schwab, Vanguard, etc. "
        "You can add custom keywords under **Manage → Overrides**."
    )
    st.stop()

# ── Hero metrics ──────────────────────────────────────────────────────────────
total_tfr    = df_tfr["Amount"].sum()
n_tfr        = len(df_tfr)
n_months     = df_tfr["YearMonth"].nunique()
avg_per_month = total_tfr / n_months if n_months else 0

st.markdown("<div class='section-title'>Overview</div>", unsafe_allow_html=True)

if has_income:
    total_income  = df_income["Amount"].sum()
    savings_rate  = total_tfr / total_income * 100 if total_income else 0
    h1, h2, h3, h4 = st.columns(4)
else:
    h1, h2, h3 = st.columns(3)

h1.markdown(render_stat_card("Total Transferred", f"${total_tfr:,.0f}", f"{n_months} months"), unsafe_allow_html=True)
h2.markdown(render_stat_card("# of Transfers",    f"{n_tfr:,}",          f"avg ${total_tfr/n_tfr:,.0f} each"), unsafe_allow_html=True)
h3.markdown(render_stat_card("Avg / Month",       f"${avg_per_month:,.0f}", "over active months"), unsafe_allow_html=True)
if has_income:
    h4.markdown(render_stat_card("Savings Rate", f"{savings_rate:.1f}%", f"of ${total_income:,.0f} income"), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

# ── Monthly transfer chart ────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Monthly Transfers</div>", unsafe_allow_html=True)

monthly = (
    df_tfr.groupby("YearMonth")["Amount"].sum()
    .reset_index().rename(columns={"Amount": "Total"})
    .sort_values("YearMonth")
)
monthly["Month"] = monthly["YearMonth"].astype(str).map(format_year_month)
avg_val = monthly["Total"].mean()

fig = go.Figure()
fig.add_trace(go.Bar(
    x=monthly["Month"], y=monthly["Total"],
    marker_color="#0EA5E9", marker_opacity=0.9,
    name="Transferred",
    hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=monthly["Month"], y=[avg_val] * len(monthly),
    mode="lines",
    line=dict(color="#94A3B8", width=1.5, dash="dash"),
    name="Avg",
    hovertemplate="Avg: $%{y:,.0f}<extra></extra>",
))
fig.update_layout(
    plot_bgcolor="white", paper_bgcolor="white",
    height=260, margin=dict(l=0, r=0, t=10, b=0),
    bargap=0.3,
    font=dict(family="DM Sans"),
    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#64748B", family="DM Sans")),
    yaxis=dict(
        showgrid=True, gridcolor="rgba(0,0,0,0.04)",
        tickprefix="$", tickformat=",.0f",
        tickfont=dict(size=12, color="#64748B", family="DM Sans"),
    ),
    legend=dict(
        orientation="h", y=1.12, x=1, xanchor="right",
        font=dict(size=12, color="#64748B", family="DM Sans"),
    ),
)
st.plotly_chart(fig, use_container_width=True)

# ── Destination breakdown ─────────────────────────────────────────────────────
st.markdown("<div class='section-title'>By Destination</div>", unsafe_allow_html=True)

dest = (
    df_tfr.groupby("Description")["Amount"]
    .agg(["sum", "count"])
    .rename(columns={"sum": "Total", "count": "Transfers"})
    .sort_values("Total", ascending=False)
    .reset_index()
    .rename(columns={"Description": "Destination"})
)
dest["% of Total"] = dest["Total"] / total_tfr * 100

dest_rows = ""
for i, row in dest.iterrows():
    bar_w = min(row["% of Total"] * 2, 100)
    dest_rows += (
        f"<tr style='border-bottom:1px solid #F1F5F9;'>"
        f"<td style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:14px;"
        f"color:#0F172A;font-weight:500;'>{row['Destination']}</td>"
        f"<td style='padding:10px 16px;'>"
        f"<div style='display:flex;align-items:center;gap:10px;'>"
        f"<div style='background:#0EA5E9;height:6px;border-radius:3px;"
        f"width:{bar_w:.0f}px;min-width:4px;'></div>"
        f"<span style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;'>"
        f"{row['% of Total']:.1f}%</span></div></td>"
        f"<td style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:13px;"
        f"color:#64748B;text-align:center;'>{int(row['Transfers'])}×</td>"
        f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:14px;"
        f"color:#0F172A;text-align:right;'>${row['Total']:,.0f}</td>"
        f"</tr>"
    )

st.markdown(
    f"<div style='background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);"
    f"border:1px solid rgba(27,58,107,0.07);overflow:hidden;margin-bottom:24px;'>"
    f"<table style='width:100%;border-collapse:collapse;'>"
    f"<thead><tr style='border-bottom:2px solid #F1F5F9;background:#F8FAFC;'>"
    f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Destination</th>"
    f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Share</th>"
    f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:center;'>Transfers</th>"
    f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;'>Total</th>"
    f"</tr></thead><tbody>{dest_rows}</tbody></table></div>",
    unsafe_allow_html=True,
)

# ── Full transfer list ────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>All Transfers</div>", unsafe_allow_html=True)

tfr_display = df_tfr.sort_values("Date", ascending=False).copy()
tfr_rows = ""
for _, row in tfr_display.iterrows():
    date_str = row["Date"].strftime("%b %d, %Y")
    tfr_rows += (
        f"<tr style='border-bottom:1px solid #F1F5F9;'>"
        f"<td style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:13px;"
        f"color:#64748B;white-space:nowrap;'>{date_str}</td>"
        f"<td style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:14px;"
        f"color:#0F172A;font-weight:500;'>{row['Description']}</td>"
        f"<td style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:12px;"
        f"color:#94A3B8;'>{row.get('Card', '')}</td>"
        f"<td style='padding:10px 12px;font-family:\"DM Mono\",monospace;font-size:14px;"
        f"color:#0EA5E9;font-weight:500;text-align:right;'>${row['Amount']:,.2f}</td>"
        f"</tr>"
    )

st.markdown(
    f"<div style='background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);"
    f"border:1px solid rgba(27,58,107,0.07);overflow:hidden;margin-bottom:24px;'>"
    f"<table style='width:100%;border-collapse:collapse;'>"
    f"<thead><tr style='border-bottom:2px solid #F1F5F9;background:#F8FAFC;'>"
    f"<th style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Date</th>"
    f"<th style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Destination</th>"
    f"<th style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Account</th>"
    f"<th style='padding:10px 12px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
    f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;'>Amount</th>"
    f"</tr></thead><tbody>{tfr_rows}</tbody></table></div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#64748B;text-align:right;'>"
    f"Showing {n_tfr:,} transfer{'s' if n_tfr != 1 else ''}</div>",
    unsafe_allow_html=True,
)
