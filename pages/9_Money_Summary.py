import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import ACCENT, inject_global_css, load_all, load_finance_config, render_drilldown, render_nav_bar, render_stat_card

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
        Money Summary
    </div>
</div>
""", unsafe_allow_html=True)

# ── Year + Card selectors ─────────────────────────────────────────────────────
sel_col, card_col, _ = st.columns([2, 1.5, 4])
with sel_col:
    available_years = sorted(df_all["Date"].dt.year.unique(), reverse=True)
    selected_year = st.selectbox("Year", available_years, index=0, label_visibility="collapsed")
with card_col:
    card_options = ["All cards"] + sorted(df_all["Card"].dropna().unique().tolist())
    selected_card = st.selectbox("Card", card_options, index=0, label_visibility="collapsed")

st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Filter data ───────────────────────────────────────────────────────────────
df = df_all.copy()
if selected_card != "All cards":
    df = df[df["Card"] == selected_card]
df_year = df[df["Date"].dt.year == selected_year]

df_exp    = df_year[df_year["RecordType"] == "expense"]
df_income = df_year[df_year["RecordType"] == "income"]
df_tfr    = df_year[df_year["RecordType"] == "transfer"]

has_income    = not df_income.empty
has_transfers = not df_tfr.empty

total_spend    = df_exp["Amount"].sum()
total_income   = df_income["Amount"].sum() if has_income else 0.0
total_invested = df_tfr["Amount"].sum()    if has_transfers else 0.0

# Proration factor: how many months of data exist for this year
months_tracked   = df_year["YearMonth"].nunique() if not df_year.empty else 0
proration_factor = months_tracked / 12 if months_tracked > 0 else 0.0
is_partial_year  = (selected_year == datetime.date.today().year) or (months_tracked < 12)

# ── Finance config contributions ──────────────────────────────────────────────
cfg = load_finance_config()

pretax_you      = 0.0
aftertax_you    = 0.0
employer_match  = 0.0

if not cfg.empty:
    for _, row in cfg.iterrows():
        annual    = float(row["AmountPerYear"]) * proration_factor
        emp       = float(row.get("EmployerMatch", 0) or 0) * proration_factor
        type_str  = str(row.get("Type", "")).lower()
        if "employer" in type_str:
            employer_match += annual + emp
        elif "pre" in type_str:
            pretax_you     += annual
            employer_match += emp
        else:
            aftertax_you   += annual
            employer_match += emp

total_contributions = pretax_you + aftertax_you + employer_match
total_saved = total_invested + total_contributions

# Gross income estimate: take-home + pre-tax deductions
gross_income_est = total_income + pretax_you if has_income else 0.0
savings_rate     = total_saved / gross_income_est * 100 if gross_income_est > 0 else None

# ── Hero metrics ──────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Overview</div>", unsafe_allow_html=True)

partial_note = f"~{months_tracked} of 12 months" if is_partial_year else f"full year"

if has_income:
    h1, h2, h3, h4 = st.columns(4)
    h1.markdown(render_stat_card("Take-home Income", f"${total_income:,.0f}", partial_note), unsafe_allow_html=True)
    h2.markdown(render_stat_card("Total Spend",      f"${total_spend:,.0f}",  partial_note, "#DC2626"), unsafe_allow_html=True)
    h3.markdown(render_stat_card("Total Saved",      f"${total_saved:,.0f}",  "transfers + contributions"), unsafe_allow_html=True)
    rate_str = f"{savings_rate:.1f}%" if savings_rate is not None else "—"
    rate_sub = "of est. gross income" if total_contributions > 0 else "of take-home"
    h4.markdown(render_stat_card("Savings Rate", rate_str, rate_sub, "#10B981"), unsafe_allow_html=True)
else:
    h1, h2, h3 = st.columns(3)
    h1.markdown(render_stat_card("Total Spend",      f"${total_spend:,.0f}",  partial_note, "#DC2626"), unsafe_allow_html=True)
    h2.markdown(render_stat_card("Total Invested",   f"${total_invested:,.0f}", "transfers to investments"), unsafe_allow_html=True)
    h3.markdown(render_stat_card("Contributions",    f"${total_contributions:,.0f}", "from Finance Config"), unsafe_allow_html=True)
    if not has_income:
        st.markdown(
            "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;"
            "margin-top:8px;'>Income metrics require a checking account CSV. "
            "Savings rate will appear once income data is loaded.</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

# ── Allocation breakdown ──────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Where Did the Money Go?</div>", unsafe_allow_html=True)

if not has_income:
    st.info(
        "Allocation chart requires income data from a checking account CSV. "
        "Without it we can't calculate what percentage each category represents."
    )
else:
    cash_remaining = max(total_income - total_spend - total_invested - aftertax_you, 0)

    segments = [
        ("Spending",                total_spend,     "#DC2626"),
        ("Investments (Transfers)", total_invested,  "#0EA5E9"),
        ("Pre-tax Contributions",   pretax_you,      "#10B981"),
        ("After-tax Contributions", aftertax_you,    "#8B5CF6"),
        ("Employer Match",          employer_match,  "#F59E0B"),
        ("Cash Remaining",          cash_remaining,  "#94A3B8"),
    ]
    alloc_labels = [label for label, val, _ in segments if val > 0]
    alloc_values = [val   for _, val, _   in segments if val > 0]
    alloc_colors = [color for _, val, color in segments if val > 0]

    donut_col, table_col = st.columns([1, 1.2])

    with donut_col:
        fig = go.Figure(go.Pie(
            labels=alloc_labels, values=alloc_values,
            hole=0.55,
            marker_colors=alloc_colors,
            textinfo="percent",
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f} &nbsp;(%{percent})<extra></extra>",
        ))
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            font=dict(family="DM Sans"),
            annotations=[dict(
                text=f"${total_income:,.0f}<br><span style='font-size:10px;'>take-home</span>",
                x=0.5, y=0.5, font_size=16, showarrow=False,
                font=dict(family="DM Mono", color="#0F172A"),
            )],
        )
        st.plotly_chart(fig, use_container_width=True)  # visual only

    with table_col:
        seg_df = pd.DataFrame([
            {"Segment": label, "Amount": val, "% of Income": val / total_income}
            for label, val, _ in segments if val > 0
        ])
        alloc_event = st.dataframe(
            seg_df,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            use_container_width=True,
            key="alloc_seg_table",
            column_config={
                "Amount": st.column_config.NumberColumn("Amount", format="$%.0f"),
                "% of Income": st.column_config.ProgressColumn(
                    "% of Income", format="%.1f%%", min_value=0, max_value=1
                ),
            },
        )
        st.markdown(
            "<div style='font-family:\"DM Sans\",sans-serif;font-size:11px;"
            "color:#94A3B8;margin-top:2px;'>Click a row to see transactions</div>",
            unsafe_allow_html=True,
        )

    # Inline drilldown from segment table
    SEGMENT_TO_RECORD = {
        "Spending":                ("expense",  "Expenses"),
        "Investments (Transfers)": ("transfer", "Investment Transfers"),
    }
    if alloc_event.selection["rows"]:
        sel_seg = seg_df.iloc[alloc_event.selection["rows"][0]]["Segment"]
        if sel_seg in SEGMENT_TO_RECORD:
            record_type, seg_title = SEGMENT_TO_RECORD[sel_seg]
            df_seg = df_year[df_year["RecordType"] == record_type]
            render_drilldown(
                df_seg.sort_values("Amount", ascending=False),
                f"{seg_title} — {selected_year} ({len(df_seg)} transactions)",
            )
        else:
            st.info(f"**{sel_seg}** comes from Finance Config — no underlying transactions to show.")

st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Contributions breakdown ───────────────────────────────────────────────────
st.markdown("<div class='section-title'>Contributions</div>", unsafe_allow_html=True)

if cfg.empty:
    st.markdown(
        "<div style='background:white;border-radius:10px;padding:20px 24px;"
        "box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);"
        "font-family:\"DM Sans\",sans-serif;font-size:14px;color:#475569;'>"
        "No contributions configured. Go to <strong>Manage → Finance Config</strong> to add "
        "your 401k, HSA, ESPP, or Roth IRA contributions. Once added, they'll appear here "
        "and factor into your savings rate."
        "</div>",
        unsafe_allow_html=True,
    )
else:
    type_colors = {
        "pre":      "#10B981",
        "after":    "#8B5CF6",
        "employer": "#F59E0B",
    }

    rows_html = ""
    contrib_total_you = 0.0
    contrib_total_emp = 0.0
    for _, row in cfg.iterrows():
        prorated_you = float(row["AmountPerYear"]) * proration_factor
        prorated_emp = float(row.get("EmployerMatch", 0) or 0) * proration_factor
        contrib_total_you += prorated_you
        contrib_total_emp += prorated_emp
        type_str  = str(row.get("Type", ""))
        type_key  = "employer" if "employer" in type_str.lower() else ("pre" if "pre" in type_str.lower() else "after")
        color     = type_colors[type_key]
        emp_str   = f"${prorated_emp:,.0f}" if prorated_emp > 0 else "—"
        rows_html += (
            f"<tr style='border-bottom:1px solid #F1F5F9;'>"
            f"<td style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:14px;"
            f"color:#0F172A;font-weight:500;'>{row['Name']}</td>"
            f"<td style='padding:10px 16px;'>"
            f"<span style='font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
            f"color:{color};background:{color}18;padding:2px 8px;border-radius:99px;'>"
            f"{type_str}</span></td>"
            f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:14px;"
            f"color:#0F172A;text-align:right;'>${prorated_you:,.0f}</td>"
            f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:13px;"
            f"color:#64748B;text-align:right;'>{emp_str}</td>"
            f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:14px;"
            f"color:#0F172A;text-align:right;'>${prorated_you + prorated_emp:,.0f}</td>"
            f"</tr>"
        )

    rows_html += (
        f"<tr style='background:#F8FAFC;'>"
        f"<td colspan='2' style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;"
        f"font-size:12px;font-weight:600;color:#475569;text-transform:uppercase;"
        f"letter-spacing:0.06em;text-align:right;'>Total</td>"
        f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:15px;"
        f"font-weight:600;color:#1B3A6B;text-align:right;'>${contrib_total_you:,.0f}</td>"
        f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:15px;"
        f"font-weight:600;color:#1B3A6B;text-align:right;'>${contrib_total_emp:,.0f}</td>"
        f"<td style='padding:10px 16px;font-family:\"DM Mono\",monospace;font-size:15px;"
        f"font-weight:600;color:#1B3A6B;text-align:right;'>${contrib_total_you + contrib_total_emp:,.0f}</td>"
        f"</tr>"
    )

    proration_note = (
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;"
        f"margin-top:8px;'>Amounts prorated to {months_tracked} of 12 months based on available data.</div>"
        if is_partial_year else ""
    )

    st.markdown(
        f"<div style='background:white;border-radius:12px;box-shadow:0 2px 8px rgba(27,58,107,0.08);"
        f"border:1px solid rgba(27,58,107,0.07);overflow:hidden;margin-bottom:8px;'>"
        f"<table style='width:100%;border-collapse:collapse;'>"
        f"<thead><tr style='border-bottom:2px solid #F1F5F9;background:#F8FAFC;'>"
        f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
        f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Account</th>"
        f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
        f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:left;'>Type</th>"
        f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
        f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;'>You</th>"
        f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
        f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;'>Employer</th>"
        f"<th style='padding:10px 16px;font-family:\"DM Sans\",sans-serif;font-size:11px;font-weight:600;"
        f"color:#475569;text-transform:uppercase;letter-spacing:0.06em;text-align:right;'>Total</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table></div>"
        f"{proration_note}",
        unsafe_allow_html=True,
    )

# ── View Transactions ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>View Transactions</div>", unsafe_allow_html=True)

drill_options = []
if not df_exp.empty:    drill_options.append("Expenses")
if has_income:          drill_options.append("Income")
if has_transfers:       drill_options.append("Investment Transfers")

if drill_options:
    drill_sel = st.radio(
        "View",
        drill_options,
        horizontal=True,
        label_visibility="collapsed",
        key="money_drill_radio",
    )
    if drill_sel == "Expenses":
        render_drilldown(df_exp.sort_values("Amount", ascending=False), f"Expenses — {selected_year} ({len(df_exp)} transactions)")
    elif drill_sel == "Income":
        render_drilldown(df_income.sort_values("Amount", ascending=False), f"Income — {selected_year} ({len(df_income)} transactions)")
    elif drill_sel == "Investment Transfers":
        render_drilldown(df_tfr.sort_values("Amount", ascending=False), f"Transfers — {selected_year} ({len(df_tfr)} transactions)")
