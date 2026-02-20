import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from utils import CAT_COLORS, date_filter, detect_subscriptions, inject_global_css, load_all

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

def _stat(label, value):
    return (f"<div style='background:white;border-radius:10px;padding:16px 20px;"
            f"box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);'>"
            f"<div style='font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
            f"color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;'>{label}</div>"
            f"<div style='font-family:\"DM Mono\",monospace;font-size:22px;font-weight:500;color:#0F172A;'>{value}</div>"
            f"</div>")

m1, m2, m3 = st.columns(3)
m1.markdown(_stat("Detected",     f"{len(subs)} subscriptions"), unsafe_allow_html=True)
m2.markdown(_stat("Est. Monthly", f"${monthly_sub:,.2f}"),       unsafe_allow_html=True)
m3.markdown(_stat("Est. Annual",  f"${annual_sub:,.2f}"),        unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Subscription table ────────────────────────────────────────────────────────
cadence_colors = {"Monthly": "#2563EB", "Annual": "#8B5CF6", "Quarterly": "#0EA5E9", "Weekly": "#F59E0B"}

rows_html = ""
for _, row in subs.sort_values("Est Monthly Cost", ascending=False).iterrows():
    color = cadence_colors.get(row["Cadence"], "#64748B")
    rows_html += f"""
<tr style="border-bottom:1px solid #F1F5F9;">
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:14px;color:#0F172A;font-weight:500;">{row['Merchant']}</td>
  <td style="padding:12px 16px;">
    <span style="font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:{color};
    background:{color}18;padding:2px 8px;border-radius:99px;">{row['Cadence']}</span>
  </td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Avg Charge']:,.2f}</td>
  <td style="padding:12px 16px;font-family:'DM Mono',monospace;font-size:14px;color:#0F172A;text-align:right;">${row['Est Monthly Cost']:,.2f}</td>
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:13px;color:#475569;text-align:right;">{int(row['Occurrences'])}×</td>
  <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:13px;color:#475569;">{str(row['Last Seen'])}</td>
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
