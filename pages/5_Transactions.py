import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from utils import CAT_COLORS, TRANSFER_KEYWORDS, date_filter, inject_global_css, load_all

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

st.markdown("<div class='section-title'>Transactions</div>", unsafe_allow_html=True)

# ── Date + card filter ────────────────────────────────────────────────────────
start, end, selected_card = date_filter(df_all, key="txn")

# ── Additional filters row ────────────────────────────────────────────────────
f1, f2, f3 = st.columns([2.5, 1.5, 1.5])
with f1:
    search = st.text_input("Search", placeholder="Merchant name…", label_visibility="collapsed")
with f2:
    all_cats = ["All categories"] + sorted(df_all["Category"].unique().tolist())
    selected_cat = st.selectbox("Category", all_cats, label_visibility="collapsed")
with f3:
    sort_by = st.selectbox(
        "Sort", ["Date ↓", "Date ↑", "Amount ↓", "Amount ↑"],
        label_visibility="collapsed",
    )

st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_all.copy()
df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]
if selected_card != "All cards":
    df = df[df["Card"] == selected_card]
if search:
    df = df[df["Description"].str.contains(search, case=False, na=False)]
if selected_cat != "All categories":
    df = df[df["Category"] == selected_cat]

sort_map = {
    "Date ↓":   ("Date", False),
    "Date ↑":   ("Date", True),
    "Amount ↓": ("Amount", False),
    "Amount ↑": ("Amount", True),
}
sort_col, sort_asc = sort_map[sort_by]
df = df.sort_values(sort_col, ascending=sort_asc).reset_index(drop=True)

# ── Summary bar ───────────────────────────────────────────────────────────────
df_exp_view    = df[df["RecordType"] == "expense"] if "RecordType" in df.columns else df
df_income_view = df[df["RecordType"] == "income"]  if "RecordType" in df.columns else df.iloc[:0]
total_spend  = df_exp_view["Amount"].sum()
total_income = df_income_view["Amount"].sum()
count        = len(df)

if total_income > 0:
    m1, m2, m3 = st.columns(3)
    m1.markdown(
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#64748B;'>"
        f"<span style='font-weight:600;color:#0F172A;font-family:\"DM Mono\",monospace;font-size:18px;'>"
        f"${total_spend:,.0f}</span>&nbsp; expenses</div>",
        unsafe_allow_html=True,
    )
    m2.markdown(
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#64748B;'>"
        f"<span style='font-weight:600;color:#16A34A;font-family:\"DM Mono\",monospace;font-size:18px;'>"
        f"+${total_income:,.0f}</span>&nbsp; income</div>",
        unsafe_allow_html=True,
    )
    m3.markdown(
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#64748B;'>"
        f"<span style='font-weight:600;color:#0F172A;font-family:\"DM Mono\",monospace;font-size:18px;'>"
        f"{count:,}</span>&nbsp; transactions</div>",
        unsafe_allow_html=True,
    )
else:
    m1, m2 = st.columns(2)
    m1.markdown(
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#64748B;'>"
        f"<span style='font-weight:600;color:#0F172A;font-family:\"DM Mono\",monospace;font-size:18px;'>"
        f"${total_spend:,.0f}</span>&nbsp; total spend</div>",
        unsafe_allow_html=True,
    )
    m2.markdown(
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#64748B;'>"
        f"<span style='font-weight:600;color:#0F172A;font-family:\"DM Mono\",monospace;font-size:18px;'>"
        f"{count:,}</span>&nbsp; transactions</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

# ── Transaction table ─────────────────────────────────────────────────────────
cat_color_map = {
    cat: CAT_COLORS[i % len(CAT_COLORS)]
    for i, cat in enumerate(sorted(df_all["Category"].unique().tolist()))
}

if df.empty:
    st.info("No transactions match your filters.")
else:
    display = df[["Date", "Description", "Category", "Amount", "Card",
                  *( ["RecordType"] if "RecordType" in df.columns else [] )]].copy()
    display["Date"] = display["Date"].dt.strftime("%b %d, %Y")

    rows_html = ""
    for _, row in display.iterrows():
        cat        = row["Category"]
        color      = cat_color_map.get(cat, "#94A3B8")
        is_income  = row.get("RecordType", "expense") == "income"
        amt_str    = f"+${row['Amount']:,.2f}" if is_income else f"${row['Amount']:,.2f}"
        amt_color  = "#16A34A" if is_income else "#0F172A"
        row_bg     = "background:#F0FDF4;" if is_income else ""
        rows_html += f"""
<tr style="border-bottom:1px solid #F1F5F9;{row_bg}">
  <td style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:13px;color:#64748B;white-space:nowrap;">{row['Date']}</td>
  <td style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:13px;color:#0F172A;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{row['Description']}</td>
  <td style="padding:10px 12px;">
    <span style="font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:{color};
    background:{color}18;padding:2px 8px;border-radius:99px;white-space:nowrap;">{cat}</span>
  </td>
  <td style="padding:10px 12px;font-family:'DM Mono',monospace;font-size:13px;color:{amt_color};text-align:right;white-space:nowrap;">{amt_str}</td>
  <td style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:12px;color:#64748B;white-space:nowrap;">{row['Card']}</td>
</tr>"""

    st.markdown(f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);
border:1px solid rgba(27,58,107,0.07);overflow:hidden;overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="border-bottom:2px solid #F1F5F9;background:#F8FAFC;">
        <th style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Date</th>
        <th style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Merchant</th>
        <th style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Category</th>
        <th style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">Amount</th>
        <th style="padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Card</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
<div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#64748B;margin-top:8px;text-align:right;">
  Showing {count:,} transactions
</div>
""", unsafe_allow_html=True)

# ── Transfer exclusions info ───────────────────────────────────────────────────
transfers = df_all[df_all["RecordType"] == "transfer"] if "RecordType" in df_all.columns else df_all.iloc[:0]
with st.expander(f"Excluded transfers ({len(transfers):,} transactions hidden from spending)"):
    st.markdown(
        "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#475569;"
        "margin-bottom:12px;'>The following keywords are matched against transaction descriptions "
        "(case-insensitive). Any checking account transaction matching these is excluded from "
        "income and expense totals. To add more, edit <code>TRANSFER_KEYWORDS</code> in "
        "<code>utils.py</code> and <code>merge.py</code>, then re-run <code>python merge.py</code>.</div>",
        unsafe_allow_html=True,
    )
    kw_html = " ".join(
        f"<span style='font-family:\"DM Mono\",monospace;font-size:12px;background:#F1F5F9;"
        f"color:#1B3A6B;padding:3px 10px;border-radius:99px;border:1px solid #E2E8F0;"
        f"display:inline-block;margin:3px 2px;'>{kw}</span>"
        for kw in sorted(TRANSFER_KEYWORDS)
    )
    st.markdown(f"<div style='margin-bottom:16px;'>{kw_html}</div>", unsafe_allow_html=True)

    if not transfers.empty:
        st.markdown("<div class='section-title' style='margin-top:4px;'>Excluded transactions</div>",
                    unsafe_allow_html=True)
        t_display = transfers[["Date", "Description", "Amount", "Card"]].copy()
        t_display["Date"]   = t_display["Date"].dt.strftime("%b %d, %Y") if hasattr(t_display["Date"].iloc[0], "strftime") else t_display["Date"]
        t_display["Amount"] = t_display["Amount"].apply(lambda x: f"${x:,.2f}")
        t_display = t_display.sort_values("Date", ascending=False).reset_index(drop=True)
        st.dataframe(t_display, use_container_width=True, hide_index=True)
