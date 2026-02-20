import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import (
    ACCENT,
    CAT_COLORS,
    chart_layout,
    compute_insights,
    date_filter,
    inject_global_css,
    load_all,
)

# Must be first Streamlit command — applies to all pages via st.navigation
st.set_page_config(
    page_title="Spending Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="auto",
)
inject_global_css()


def dashboard():
    # ── Load data ─────────────────────────────────────────────────────────────
    df_all = load_all()

    if df_all.empty:
        st.error("No CSV files found in `data/`. Drop your exports there and click Reload.")
        if st.button("↺ Reload"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    # ── Header banner ─────────────────────────────────────────────────────────
    st.markdown("""
<div style="
    background: linear-gradient(135deg, #1B3A6B 0%, #2563EB 100%);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 20px;
">
    <div style="font-family:'DM Mono',monospace;font-size:28px;font-weight:500;color:white;letter-spacing:-0.02em;">
        Spending Dashboard
    </div>
    <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:rgba(255,255,255,0.65);margin-top:6px;">
        Your personal finance overview
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Hero placeholder (fills in after filters are applied) ─────────────────
    hero_slot = st.empty()

    # ── Filter bar ────────────────────────────────────────────────────────────
    start, end, selected_card = date_filter(df_all, key="dash", default_preset="Last 3 months")

    st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

    # ── Apply filters ─────────────────────────────────────────────────────────
    df = df_all.copy()
    if selected_card != "All cards":
        df = df[df["Card"] == selected_card]
    df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]

    if df.empty:
        st.warning("No transactions match the current filters.")
        st.stop()

    # Write to session state for detail pages
    st.session_state["filtered_df"]  = df
    st.session_state["df_all"]       = df_all
    st.session_state["filter_card"]  = selected_card
    st.session_state["filter_start"] = start
    st.session_state["filter_end"]   = end

    # Split income vs expenses — income must never inflate spending totals
    df_exp    = df[df["RecordType"] == "expense"]
    df_income = df[df["RecordType"] == "income"]
    has_income = not df_income.empty

    if df_exp.empty:
        st.warning("No expense transactions match the current filters.")
        st.stop()

    # ── Compute metrics ───────────────────────────────────────────────────────
    monthly_totals = df_exp.groupby("YearMonth")["Amount"].sum().sort_index()
    current_period = df_exp["YearMonth"].max()
    this_month_amt = monthly_totals.get(current_period, 0)
    prev_period    = current_period - 1
    mom_delta      = this_month_amt - monthly_totals.get(prev_period, 0)

    complete_periods = sorted([p for p in monthly_totals.index if p < current_period])
    last_3 = complete_periods[-3:] if len(complete_periods) >= 3 else complete_periods
    avg_3m = monthly_totals[monthly_totals.index.isin(last_3)].mean() if last_3 else 0

    current_year = datetime.date.today().year
    ytd = df_all[
        (df_all["Date"].dt.year == current_year) & (df_all["RecordType"] == "expense")
    ]["Amount"].sum()

    # Income metrics (only computed if checking data is loaded)
    if has_income:
        income_this_month = df_income[df_income["YearMonth"] == current_period]["Amount"].sum()
        net_this_month    = income_this_month - this_month_amt
        net_class = "down" if net_this_month >= 0 else "up"   # green if saving, red if over
        net_arrow = "+" if net_this_month >= 0 else "-"

    # ── Hero cards ────────────────────────────────────────────────────────────
    delta_class = "up" if mom_delta > 0 else "down"
    delta_arrow = "↑" if mom_delta > 0 else "↓"
    mom_vs_avg  = this_month_amt - avg_3m
    mom_avg_cls = "up" if mom_vs_avg > 0 else "down"
    mom_avg_arr = "↑" if mom_vs_avg > 0 else "↓"

    with hero_slot.container():
        cols = "repeat(4,1fr)" if has_income else "repeat(3,1fr)"
        income_card = f"""
    <div class="card">
        <div class="card-label">Income This Month</div>
        <div class="card-value">${income_this_month:,.0f}</div>
        <div class="card-sub {net_class}">{net_arrow} ${abs(net_this_month):,.0f} net</div>
    </div>""" if has_income else ""

        st.markdown(f"""
<div style="display:grid;grid-template-columns:{cols};gap:14px;margin-bottom:8px;">
    <div class="card">
        <div class="card-label">This Month</div>
        <div class="card-value">${this_month_amt:,.0f}</div>
        <div class="card-sub {delta_class}">{delta_arrow} ${abs(mom_delta):,.0f} vs last month</div>
    </div>
    <div class="card">
        <div class="card-label">YTD Spend</div>
        <div class="card-value">${ytd:,.0f}</div>
        <div class="card-sub neutral">{current_year} to date</div>
    </div>
    <div class="card">
        <div class="card-label">3-Month Average</div>
        <div class="card-value">${avg_3m:,.0f}</div>
        <div class="card-sub {mom_avg_cls}">{mom_avg_arr} ${abs(mom_vs_avg):,.0f} vs this month</div>
    </div>{income_card}
</div>
""", unsafe_allow_html=True)

    # ── Insights ──────────────────────────────────────────────────────────────
    insights = compute_insights(df_exp)
    st.markdown("<div class='section-title'>Insights</div>", unsafe_allow_html=True)
    if not insights:
        st.markdown(
            "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#94A3B8;"
            "padding:14px 0 8px;'>Need at least 2 months of data in the selected range to surface insights.</div>",
            unsafe_allow_html=True,
        )
    if insights:
        icon_map = {"spike": "↑", "drop": "↓", "info": "◆"}
        cards_html = ""
        for ins in insights:
            ind   = ins["indicator"]
            icon  = icon_map.get(ind, "◆")
            amt   = ins["dollar_amount"]
            chg   = ins["dollar_change"]
            chg_s = f"+${chg:,.0f}" if chg > 0 else f"-${abs(chg):,.0f}"
            delta_col = "#DC2626" if ind == "spike" else ("#16A34A" if ind == "drop" else "#1B3A6B")
            cards_html += f"""
<div class="insight-card {ind}">
    <div class="insight-icon" style="color:{delta_col};">{icon}</div>
    <div class="insight-headline">{ins['headline']}</div>
    <div class="insight-amount">${amt:,.0f}</div>
    <div class="insight-delta" style="color:{delta_col};">{chg_s} vs avg</div>
</div>"""
        st.markdown(f"<div class='insight-row'>{cards_html}</div>", unsafe_allow_html=True)

    # ── Monthly spend chart ───────────────────────────────────────────────────
    monthly = (
        df_exp.groupby("YearMonth")["Amount"]
        .sum().reset_index()
        .rename(columns={"Amount": "Total"})
        .sort_values("YearMonth")
    )
    monthly["Month"] = monthly["YearMonth"].astype(str)
    n_months    = len(monthly)
    avg_monthly = monthly["Total"].mean() if n_months else 0

    fig_monthly = go.Figure()
    # Income bars (behind expenses) — only when checking data is present
    if has_income:
        monthly_income = (
            df_income.groupby("YearMonth")["Amount"]
            .sum().reset_index()
            .rename(columns={"Amount": "Income"})
            .sort_values("YearMonth")
        )
        monthly_income["Month"] = monthly_income["YearMonth"].astype(str)
        fig_monthly.add_trace(go.Bar(
            x=monthly_income["Month"], y=monthly_income["Income"],
            marker_color="#10B981", marker_opacity=0.35,
            name="Income",
            hovertemplate="<b>%{x}</b><br>Income: $%{y:,.0f}<extra></extra>",
        ))
    fig_monthly.add_trace(go.Bar(
        x=monthly["Month"], y=monthly["Total"],
        marker_color=ACCENT, marker_opacity=1.0,
        name="Spend",
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
    fig_monthly.add_trace(go.Scatter(
        x=monthly["Month"], y=[avg_monthly] * len(monthly),
        mode="lines",
        line=dict(color="#94A3B8", width=1.5, dash="dash"),
        name="Avg spend",
        hovertemplate="Avg: $%{y:,.0f}<extra></extra>",
    ))
    fig_monthly.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        height=280, margin=dict(l=0, r=0, t=10, b=0),
        bargap=0.3,
        font=dict(family="DM Sans"),
        xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#64748B", family="DM Sans")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.04)",
                   tickprefix="$", tickformat=",.0f",
                   tickfont=dict(size=12, color="#64748B", family="DM Sans")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                    font=dict(size=12, color="#64748B", family="DM Sans")),
    )
    st.markdown("<div class='section-title'>Monthly Spend</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_monthly, use_container_width=True)

    # ── Category breakdown ────────────────────────────────────────────────────
    cat = (
        df_exp.groupby("Category")["Amount"].sum()
        .sort_values(ascending=False)
        .reset_index().rename(columns={"Amount": "Total"})
    )
    total_spend = cat["Total"].sum()
    cat["Pct"] = cat["Total"] / total_spend * 100

    # Per-category trend vs 3-month baseline
    current_by_cat  = df_exp[df_exp["YearMonth"] == current_period].groupby("Category")["Amount"].sum()
    baseline_by_cat = (
        df_exp[df_exp["YearMonth"].isin(last_3)].groupby("Category")["Amount"].sum() / len(last_3)
        if last_3 else pd.Series(dtype=float)
    )

    st.markdown("<div class='section-title'>Spending by Category</div>", unsafe_allow_html=True)

    rows_html = ""
    for i, row in cat.head(7).iterrows():
        color = CAT_COLORS[i % len(CAT_COLORS)]
        this_m = current_by_cat.get(row["Category"], 0)
        base   = baseline_by_cat.get(row["Category"], 0)
        if base > 0:
            pct_chg = (this_m - base) / base
            if pct_chg > 0.10:
                trend_icon, trend_color, trend_label = "↑", "#DC2626", f"+{pct_chg*100:.0f}%"
            elif pct_chg < -0.10:
                trend_icon, trend_color, trend_label = "↓", "#16A34A", f"{pct_chg*100:.0f}%"
            else:
                trend_icon, trend_color, trend_label = "→", "#94A3B8", "stable"
        else:
            trend_icon, trend_color, trend_label = "◆", "#94A3B8", "new"

        rows_html += f"""
<div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #F1F5F9;">
  <div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;margin-right:12px;"></div>
  <div style="flex:1;font-family:'DM Sans',sans-serif;font-size:14px;color:#0F172A;">{row['Category']}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#94A3B8;margin-right:20px;width:32px;text-align:right;">{row['Pct']:.0f}%</div>
  <div style="font-family:'DM Mono',monospace;font-size:15px;color:#0F172A;margin-right:20px;width:72px;text-align:right;">${row['Total']:,.0f}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;color:{trend_color};width:56px;text-align:right;">{trend_icon} {trend_label}</div>
</div>"""

    st.markdown(
        f"<div style='background:white;border-radius:12px;padding:4px 20px 4px;box-shadow:var(--shadow-md);"
        f"border:1px solid rgba(27,58,107,0.07);margin-bottom:24px;'>{rows_html}</div>",
        unsafe_allow_html=True,
    )

    # ── Explore navigation ────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>Explore</div>", unsafe_allow_html=True)
    nav1, nav2, nav3, nav4 = st.columns(4)
    with nav1:
        if st.button("🧾 Transactions", use_container_width=True):
            st.switch_page("pages/5_Transactions.py")
    with nav2:
        if st.button("📊 Categories", use_container_width=True):
            st.switch_page("pages/1_Categories.py")
    with nav3:
        if st.button("🏪 Merchants", use_container_width=True):
            st.switch_page("pages/2_Merchants.py")
    with nav4:
        if st.button("🔄 Subscriptions", use_container_width=True):
            st.switch_page("pages/3_Subscriptions.py")


# ── Multipage navigation ──────────────────────────────────────────────────────
pg = st.navigation({
    "Overview": [
        st.Page(dashboard, title="Dashboard", icon="💳", default=True),
    ],
    "Explore": [
        st.Page("pages/5_Transactions.py",  title="Transactions",  icon="🧾"),
        st.Page("pages/1_Categories.py",    title="Categories",    icon="📊"),
        st.Page("pages/2_Merchants.py",     title="Merchants",     icon="🏪"),
        st.Page("pages/3_Subscriptions.py", title="Subscriptions", icon="🔄"),
    ],
})
pg.run()
