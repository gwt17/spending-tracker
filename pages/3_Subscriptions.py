import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from utils import date_filter, detect_subscriptions, inject_global_css, load_all, render_nav_bar

inject_global_css()
render_nav_bar()

# ── Load data (always fresh — @st.cache_data handles perf) ───────────────────
df_all = load_all()
if df_all.empty:
    st.error("No data found. Return to the main page or drop CSVs into `data/`.")
    st.stop()

st.markdown("<div class='section-title'>Subscriptions</div>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
start, end, selected_card = date_filter(df_all, key="subs", default_preset="All time")
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

# ── Subscriptions ─────────────────────────────────────────────────────────────
subs = detect_subscriptions(df)

if subs.empty:
    st.info("No subscriptions detected. Works best with 6+ months of data and 'All time' selected.")
    st.stop()

monthly_sub  = subs["Est Monthly Cost"].sum()
annual_sub   = monthly_sub * 12

st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:8px;">
    <div class="card card-primary">
        <div class="card-label">Est. Annual Cost</div>
        <div class="card-value">${annual_sub:,.0f}</div>
        <div class="card-sub neutral">${monthly_sub:,.0f} / month</div>
    </div>
    <div class="card">
        <div class="card-label">Est. Monthly Cost</div>
        <div class="card-value">${monthly_sub:,.0f}</div>
        <div class="card-sub neutral">across all subscriptions</div>
    </div>
    <div class="card">
        <div class="card-label">Detected</div>
        <div class="card-value">{len(subs)}</div>
        <div class="card-sub neutral">subscriptions</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Subscription table ────────────────────────────────────────────────────────
cadence_colors = {"Monthly": "#2563EB", "Annual": "#8B5CF6", "Quarterly": "#0EA5E9", "Weekly": "#F59E0B"}

rows_html = ""
for _, row in subs.sort_values("Est Monthly Cost", ascending=False).iterrows():
    color      = cadence_colors.get(row["Cadence"], "#64748B")
    est_annual = row["Est Monthly Cost"] * 12
    rows_html += f"""
<tr style="border-bottom:1px solid #F1F5F9;">
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:14px;color:#0F172A;font-weight:500;">{row['Merchant']}</td>
  <td style="padding:12px 16px;">
    <span style="font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:{color};
    background:{color}18;padding:2px 8px;border-radius:99px;">{row['Cadence']}</span>
  </td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Avg Charge']:,.2f}</td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Est Monthly Cost']:,.2f}</td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;font-weight:600;color:#1B3A6B;text-align:right;">${est_annual:,.0f}</td>
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:13px;color:#475569;text-align:right;">{int(row['Occurrences'])}×</td>
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:13px;color:#475569;">{str(row['Last Seen'])}</td>
</tr>"""

annual_total = subs["Est Monthly Cost"].sum() * 12
rows_html += f"""
<tr style="background:#F8FAFC;">
  <td colspan="4" style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:600;
  color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Total Est. Annual</td>
  <td style="padding:10px 16px;font-family:'DM Mono',monospace;font-size:15px;font-weight:600;color:#1B3A6B;text-align:right;">${annual_total:,.0f}</td>
  <td colspan="2"></td>
</tr>"""

st.markdown(f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);
border:1px solid rgba(27,58,107,0.07);overflow:hidden;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="border-bottom:2px solid #F1F5F9;background:#F8FAFC;">
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Merchant</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Cadence</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Per Charge</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Est / Month</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Est Annual</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Occurrences</th>
        <th style="padding:10px 16px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Last Seen</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown(
    f"<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#64748B;margin-top:10px;'>"
    f"Detected using heuristics: ≥2 charges with consistent amounts at regular intervals. "
    f"Use <strong>All time</strong> for best results.</div>",
    unsafe_allow_html=True,
)
