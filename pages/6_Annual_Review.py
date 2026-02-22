import calendar
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import ACCENT, CAT_COLORS, chart_layout, detect_subscriptions, inject_global_css, load_all, render_drilldown

inject_global_css()

# ── Nav bar ───────────────────────────────────────────────────────────────────
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

# ── Load data ─────────────────────────────────────────────────────────────────
df_all = load_all()
if df_all.empty:
    st.error("No data found. Return to the main page or drop CSVs into `data/`.")
    st.stop()

# ── Header banner ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1B3A6B 0%, #2563EB 100%);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 20px;
">
    <div style="font-family:'DM Mono',monospace;font-size:28px;font-weight:500;color:white;letter-spacing:-0.02em;">
        Annual Review
    </div>
    <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:rgba(255,255,255,0.65);margin-top:6px;">
        Year-over-year spending breakdown
    </div>
</div>
""", unsafe_allow_html=True)

# ── Year + Card selectors ─────────────────────────────────────────────────────
sel_col, card_col, _ = st.columns([2, 1.5, 4])
with sel_col:
    available_years = sorted(df_all["Date"].dt.year.unique(), reverse=True)
    selected_year = st.selectbox(
        "Year",
        available_years,
        index=0,
        label_visibility="collapsed",
        format_func=lambda y: str(y),
    )
with card_col:
    card_options = ["All cards"] + sorted(df_all["Card"].dropna().unique().tolist())
    selected_card = st.selectbox(
        "Card",
        card_options,
        index=0,
        label_visibility="collapsed",
    )

st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Filter data ───────────────────────────────────────────────────────────────
df_card = df_all.copy()
if selected_card != "All cards":
    df_card = df_card[df_card["Card"] == selected_card]

df_year  = df_card[df_card["Date"].dt.year == selected_year]
df_exp   = df_year[df_year["RecordType"] == "expense"]
df_income = df_year[df_year["RecordType"] == "income"]
has_income = not df_income.empty

if df_exp.empty:
    st.warning(f"No expense transactions found for {selected_year}.")
    st.stop()

# ── Stat card helper ──────────────────────────────────────────────────────────
def _stat(label, value, sub=None):
    sub_html = (
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;"
        f"color:#64748B;margin-top:4px;'>{sub}</div>"
    ) if sub else ""
    return (
        f"<div style='background:white;border-radius:10px;padding:16px 20px;"
        f"box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);'>"
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
        f"color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;'>{label}</div>"
        f"<div style='font-family:\"DM Mono\",monospace;font-size:22px;font-weight:500;color:#0F172A;'>{value}</div>"
        f"{sub_html}</div>"
    )

# ── Hero metrics ──────────────────────────────────────────────────────────────
total_spend  = df_exp["Amount"].sum()
n_months_active = df_exp["YearMonth"].nunique()
avg_per_month = total_spend / n_months_active if n_months_active else 0
n_txns = len(df_exp)
total_income = df_income["Amount"].sum() if has_income else 0

st.markdown("<div class='section-title'>Overview</div>", unsafe_allow_html=True)

if has_income:
    h1, h2, h3, h4 = st.columns(4)
else:
    h1, h2, h3 = st.columns(3)

h1.markdown(_stat("Total Spend",    f"${total_spend:,.0f}",    f"{n_months_active} months tracked"),  unsafe_allow_html=True)
h2.markdown(_stat("Avg / Month",    f"${avg_per_month:,.0f}",  f"across active months"),              unsafe_allow_html=True)
h3.markdown(_stat("Transactions",   f"{n_txns:,}",             f"{selected_year}"),                   unsafe_allow_html=True)
if has_income:
    net = total_income - total_spend
    net_label = f"+${net:,.0f} saved" if net >= 0 else f"-${abs(net):,.0f} over"
    h4.markdown(_stat("Total Income", f"${total_income:,.0f}", net_label), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

# ── Month-by-month bar chart ──────────────────────────────────────────────────
st.markdown("<div class='section-title'>Month-by-Month Spend</div>", unsafe_allow_html=True)

# Build full Jan–Dec grid for selected year
all_months = [f"{selected_year}-{m:02d}" for m in range(1, 13)]
month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

monthly_exp = (
    df_exp.groupby("YearMonth")["Amount"].sum()
    .reset_index()
    .rename(columns={"Amount": "Total"})
)
monthly_exp["Month"] = monthly_exp["YearMonth"].astype(str)
month_map = dict(zip(monthly_exp["Month"], monthly_exp["Total"]))
y_current = [month_map.get(m, 0) for m in all_months]

# Prior year overlay
prior_year = selected_year - 1
df_prior = df_card[df_card["Date"].dt.year == prior_year]
df_prior_exp = df_prior[df_prior["RecordType"] == "expense"]
prior_months = [f"{prior_year}-{m:02d}" for m in range(1, 13)]
prior_exp = (
    df_prior_exp.groupby("YearMonth")["Amount"].sum()
    .reset_index()
    .rename(columns={"Amount": "Total"})
)
prior_exp["Month"] = prior_exp["YearMonth"].astype(str)
prior_map = dict(zip(prior_exp["Month"], prior_exp["Total"]))
y_prior = [prior_map.get(m, 0) for m in prior_months]
has_prior = any(v > 0 for v in y_prior)

avg_val = sum(v for v in y_current if v > 0) / max(sum(1 for v in y_current if v > 0), 1)

fig_monthly = go.Figure()

if has_prior:
    fig_monthly.add_trace(go.Bar(
        x=month_labels, y=y_prior,
        marker_color="#94A3B8", marker_opacity=0.35,
        name=str(prior_year),
        hovertemplate="<b>%{x} " + str(prior_year) + "</b><br>$%{y:,.0f}<extra></extra>",
    ))

fig_monthly.add_trace(go.Bar(
    x=month_labels, y=y_current,
    marker_color=ACCENT, marker_opacity=1.0,
    name=str(selected_year),
    hovertemplate="<b>%{x} " + str(selected_year) + "</b><br>$%{y:,.0f}<extra></extra>",
))

fig_monthly.add_trace(go.Scatter(
    x=month_labels, y=[avg_val] * 12,
    mode="lines",
    line=dict(color="#94A3B8", width=1.5, dash="dash"),
    name="Avg (active months)",
    hovertemplate="Avg: $%{y:,.0f}<extra></extra>",
))

fig_monthly.update_layout(
    barmode="group",
    plot_bgcolor="white", paper_bgcolor="white",
    height=300, margin=dict(l=0, r=0, t=10, b=0),
    bargap=0.25,
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
st.markdown(
    "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;margin-bottom:4px;'>"
    "Click a bar to see that month's transactions.</div>",
    unsafe_allow_html=True,
)
monthly_event = st.plotly_chart(fig_monthly, use_container_width=True, on_select="rerun", key="ar_monthly")

# ── Monthly drilldown ─────────────────────────────────────────────────────────
if monthly_event.selection["points"]:
    pts = monthly_event.selection["points"]
    # The x-axis uses month_labels (e.g. "Jan", "Feb"). Map back to full month string.
    sel_label = pts[0].get("x")
    if sel_label:
        month_num = list(__import__("calendar").month_abbr).index(sel_label)
        if month_num > 0:
            sel_ym = f"{selected_year}-{month_num:02d}"
            df_month_drill = df_exp[df_exp["YearMonth"].astype(str) == sel_ym]
            if not df_month_drill.empty:
                render_drilldown(
                    df_month_drill.sort_values("Amount", ascending=False),
                    f"{sel_label} {selected_year} — {len(df_month_drill)} transactions",
                )

# ── Spend by Category ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Spend by Category</div>", unsafe_allow_html=True)

cat = (
    df_exp.groupby("Category")["Amount"].sum()
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={"Amount": "Total"})
)
cat["Pct"] = cat["Total"] / total_spend * 100

fig_cat = go.Figure(go.Bar(
    x=cat["Total"],
    y=cat["Category"],
    orientation="h",
    marker_color=[CAT_COLORS[i % len(CAT_COLORS)] for i in range(len(cat))],
    hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
))
fig_cat.update_layout(
    plot_bgcolor="white", paper_bgcolor="white",
    height=max(200, len(cat) * 32),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(
        showgrid=True, gridcolor="rgba(0,0,0,0.04)",
        tickprefix="$", tickformat=",.0f",
        tickfont=dict(size=11, color="#64748B", family="DM Sans"),
    ),
    yaxis=dict(
        autorange="reversed",
        tickfont=dict(size=12, color="#475569", family="DM Sans"),
    ),
    font=dict(family="DM Sans"),
)
st.markdown(
    "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;"
    "margin-bottom:4px;'>Click a bar to drill into transactions for that category.</div>",
    unsafe_allow_html=True,
)
cat_event = st.plotly_chart(fig_cat, use_container_width=True, on_select="rerun", key="ar_cat_bar")

# ── Category drilldown ───────────────────────────────────────────────────────
selected_cat = None
if cat_event.selection["points"]:
    selected_cat = cat_event.selection["points"][0].get("y")

if selected_cat:
    df_drill = df_exp[df_exp["Category"] == selected_cat].sort_values("Amount", ascending=False)
    render_drilldown(df_drill, f"{selected_cat} — {selected_year} ({len(df_drill)} transactions)")

# ── Fixed vs Variable ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Fixed vs Variable</div>", unsafe_allow_html=True)

# Detect subs from full card-filtered history (not year-scoped) for best detection
subs = detect_subscriptions(df_card[df_card["RecordType"] == "expense"])

if not subs.empty:
    sub_merchants = set(subs["Merchant"].str.lower())
    df_exp_lower = df_exp.copy()
    df_exp_lower["_desc_lower"] = df_exp_lower["Description"].str.lower()
    fixed_mask = df_exp_lower["_desc_lower"].apply(
        lambda d: any(m in d for m in sub_merchants)
    )
    fixed_spend    = df_exp[fixed_mask]["Amount"].sum()
    variable_spend = total_spend - fixed_spend
else:
    fixed_spend    = 0.0
    variable_spend = total_spend

donut_col, stat_col = st.columns([1, 1.2])

with donut_col:
    if fixed_spend > 0:
        fig_donut = go.Figure(go.Pie(
            labels=["Fixed (subscriptions)", "Variable"],
            values=[fixed_spend, variable_spend],
            hole=0.6,
            marker_colors=[ACCENT, "#0EA5E9"],
            textinfo="percent",
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
        ))
        fig_donut.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            height=240, margin=dict(l=0, r=0, t=10, b=0),
            showlegend=True,
            legend=dict(font=dict(size=12, color="#64748B", family="DM Sans")),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.markdown(
            "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#94A3B8;"
            "padding:40px 0;text-align:center;'>No subscriptions detected</div>",
            unsafe_allow_html=True,
        )

with stat_col:
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    fixed_pct    = fixed_spend / total_spend * 100 if total_spend else 0
    variable_pct = 100 - fixed_pct
    s1, s2 = st.columns(2)
    s1.markdown(
        _stat("Fixed Spend",    f"${fixed_spend:,.0f}",    f"{fixed_pct:.0f}% of total"),
        unsafe_allow_html=True,
    )
    s2.markdown(
        _stat("Variable Spend", f"${variable_spend:,.0f}", f"{variable_pct:.0f}% of total"),
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

# ── Top Merchants ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Top Merchants</div>", unsafe_allow_html=True)

merchants = (
    df_exp.groupby("Description")["Amount"].sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
    .rename(columns={"Description": "Merchant", "Amount": "Total"})
)
merchants["Pct"] = merchants["Total"] / total_spend * 100

merch_rows = ""
for i, row in merchants.iterrows():
    bar_width = row["Pct"] * 2  # scale: 50% spend → 100px bar
    merch_rows += f"""
<tr style="border-bottom:1px solid #F1F5F9;">
  <td style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:13px;color:#64748B;font-weight:600;width:32px;text-align:right;">{i+1}</td>
  <td style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:14px;color:#0F172A;font-weight:500;">{row['Merchant']}</td>
  <td style="padding:10px 16px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="background:{ACCENT};height:6px;border-radius:3px;width:{bar_width:.0f}px;min-width:4px;"></div>
      <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#94A3B8;">{row['Pct']:.1f}%</span>
    </div>
  </td>
  <td style="padding:10px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Total']:,.0f}</td>
</tr>"""

st.markdown(f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);
border:1px solid rgba(27,58,107,0.07);overflow:hidden;margin-bottom:24px;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="border-bottom:2px solid #F1F5F9;background:#F8FAFC;">
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">#</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Merchant</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Share</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Total</th>
      </tr>
    </thead>
    <tbody>{merch_rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

# ── Subscription Annual Cost ──────────────────────────────────────────────────
if not subs.empty:
    st.markdown("<div class='section-title'>Subscription Annual Cost</div>", unsafe_allow_html=True)

    cadence_colors = {"Monthly": "#2563EB", "Annual": "#8B5CF6", "Quarterly": "#0EA5E9", "Weekly": "#F59E0B"}

    sub_rows = ""
    for _, row in subs.sort_values("Est Monthly Cost", ascending=False).iterrows():
        color     = cadence_colors.get(row["Cadence"], "#64748B")
        est_annual = row["Est Monthly Cost"] * 12
        sub_rows += f"""
<tr style="border-bottom:1px solid #F1F5F9;">
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:14px;color:#0F172A;font-weight:500;">{row['Merchant']}</td>
  <td style="padding:12px 16px;">
    <span style="font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:{color};
    background:{color}18;padding:2px 8px;border-radius:99px;">{row['Cadence']}</span>
  </td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Avg Charge']:,.2f}</td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Est Monthly Cost']:,.2f}</td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;font-weight:600;color:#1B3A6B;text-align:right;">${est_annual:,.0f}</td>
</tr>"""

    annual_total = subs["Est Monthly Cost"].sum() * 12
    sub_rows += f"""
<tr style="background:#F8FAFC;">
  <td colspan="4" style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;color:#475569;text-align:right;text-transform:uppercase;letter-spacing:0.06em;">Total Est. Annual</td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:15px;font-weight:600;color:#1B3A6B;text-align:right;">${annual_total:,.0f}</td>
</tr>"""

    st.markdown(f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);
border:1px solid rgba(27,58,107,0.07);overflow:hidden;margin-bottom:24px;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="border-bottom:2px solid #F1F5F9;background:#F8FAFC;">
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Merchant</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Cadence</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Per Charge</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Est / Month</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Est Annual</th>
      </tr>
    </thead>
    <tbody>{sub_rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)
