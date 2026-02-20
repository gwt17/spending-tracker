import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Spending Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme ───────────────────────────────────────────────────────────────────────
ACCENT     = "#1B3A6B"
CAT_COLORS = ["#1B3A6B","#2563EB","#0EA5E9","#06B6D4","#8B5CF6","#EC4899","#F59E0B","#10B981"]

st.markdown(f"""
<style>
html, body, .stApp {{
    background-color: #F0F4FA;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}
#MainMenu, footer, .stDeployButton {{ display: none !important; }}

/* Sidebar */
section[data-testid="stSidebar"] > div:first-child {{
    background-color: {ACCENT};
    padding-top: 2rem;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] .stMarkdown {{
    color: rgba(255,255,255,0.8) !important;
}}
section[data-testid="stSidebar"] h2 {{
    color: white !important;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.04em;
}}
section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.15) !important;
}}

/* Metric cards */
.card {{
    background: white;
    border-radius: 12px;
    padding: 22px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
}}
.card-accent {{ border-top: 3px solid {ACCENT}; }}
.card-label {{
    color: #94A3B8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.card-value {{
    color: #0F172A;
    font-size: 30px;
    font-weight: 700;
    margin-top: 8px;
    line-height: 1;
}}
.card-sub {{ font-size: 13px; margin-top: 6px; font-weight: 500; }}
.up      {{ color: #DC2626; }}
.down    {{ color: #16A34A; }}
.neutral {{ color: #94A3B8; }}

/* Section titles */
.section-title {{
    color: #0F172A;
    font-size: 17px;
    font-weight: 700;
    margin: 28px 0 12px 0;
}}
</style>
""", unsafe_allow_html=True)

# ── Card format config ──────────────────────────────────────────────────────────
# Add an entry here for each CSV filename in data/ (key = filename without extension,
# lowercase). If no match is found, "default" (Chase format) is used.
#
# amount_sign: -1 if negative = expense (Chase), 1 if positive = expense
#
# Example for a second card:
#   "amex": {
#       "date_col":    "Date",
#       "desc_col":    "Description",
#       "cat_col":     "Category",
#       "amount_col":  "Amount",
#       "amount_sign": 1,
#   },

CARD_CONFIG = {
    "default": {
        "date_col":    "Transaction Date",
        "desc_col":    "Description",
        "cat_col":     "Category",
        "amount_col":  "Amount",
        "amount_sign": -1,
    },
}

# ── Data loading ────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"


def load_card(path: Path) -> pd.DataFrame:
    card_key = path.stem.lower()
    cfg = CARD_CONFIG.get(card_key, CARD_CONFIG["default"])
    raw = pd.read_csv(path)
    raw.columns = raw.columns.str.strip()
    df = pd.DataFrame()
    df["Date"]        = pd.to_datetime(raw[cfg["date_col"]])
    df["Description"] = raw[cfg["desc_col"]].str.strip()
    df["Category"]    = (
        raw[cfg["cat_col"]].str.strip()
        if cfg["cat_col"] in raw.columns
        else "Uncategorized"
    )
    df["Amount"] = raw[cfg["amount_col"]] * cfg["amount_sign"]
    df["Card"]   = path.stem.title()
    df = df[df["Amount"] > 0].copy()
    return df


@st.cache_data
def load_all() -> pd.DataFrame:
    merged = DATA_DIR / "merged.csv"
    if merged.exists():
        df = pd.read_csv(merged, parse_dates=["Date"])
    else:
        csvs = sorted(DATA_DIR.glob("*.[Cc][Ss][Vv]"))
        if not csvs:
            return pd.DataFrame()
        df = pd.concat([load_card(p) for p in csvs], ignore_index=True)
    df["YearMonth"] = df["Date"].dt.to_period("M")
    return df


# ── Load ────────────────────────────────────────────────────────────────────────
df_all = load_all()

if df_all.empty:
    st.error("No CSV files found in `data/`. Drop your exports there and click Reload.")
    if st.button("Reload"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")
    cards = ["All"] + sorted(df_all["Card"].unique().tolist())
    selected_card = st.selectbox("Card", cards)
    min_date  = df_all["Date"].min().date()
    max_date  = df_all["Date"].max().date()
    date_range = st.date_input("Date Range", value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)
    all_cats      = sorted(df_all["Category"].unique().tolist())
    selected_cats = st.multiselect("Categories", all_cats, default=all_cats)
    st.markdown("---")
    if st.button("Reload Data"):
        st.cache_data.clear()
        st.rerun()

# ── Apply filters ────────────────────────────────────────────────────────────────
df = df_all.copy()
if selected_card != "All":
    df = df[df["Card"] == selected_card]
if len(date_range) == 2:
    start, end = date_range
    df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]
if selected_cats:
    df = df[df["Category"].isin(selected_cats)]
if df.empty:
    st.warning("No transactions match the current filters.")
    st.stop()

# ── Compute metrics ──────────────────────────────────────────────────────────────
monthly_totals = df.groupby("YearMonth")["Amount"].sum()
total_spend    = df["Amount"].sum()
n_months       = df["YearMonth"].nunique()
avg_monthly    = total_spend / n_months if n_months else 0
current_period = df["YearMonth"].max()
this_month_amt = monthly_totals.get(current_period, 0)
prev_period    = current_period - 1
prev_month_amt = monthly_totals.get(prev_period, 0)
mom_delta      = this_month_amt - prev_month_amt
current_year   = df["Date"].max().year
ytd            = df[df["Date"].dt.year == current_year]["Amount"].sum()
cutoff_12m     = df["Date"].max() - pd.DateOffset(months=12)
rolling_12     = df[df["Date"] >= cutoff_12m]["Amount"].sum()

# ── Page title ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='font-size:26px;font-weight:800;color:#0F172A;margin-bottom:20px;'>"
    "Spending Overview</div>",
    unsafe_allow_html=True,
)

# ── Hero cards ───────────────────────────────────────────────────────────────────
delta_class = "up" if mom_delta > 0 else "down"
delta_arrow = "↑" if mom_delta > 0 else "↓"

st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;">
    <div class="card card-accent">
        <div class="card-label">YTD Spend</div>
        <div class="card-value">${ytd:,.0f}</div>
        <div class="card-sub neutral">{current_year} to date</div>
    </div>
    <div class="card card-accent">
        <div class="card-label">12-Month Rolling</div>
        <div class="card-value">${rolling_12:,.0f}</div>
        <div class="card-sub neutral">trailing 12 months</div>
    </div>
    <div class="card card-accent">
        <div class="card-label">Monthly Average</div>
        <div class="card-value">${avg_monthly:,.0f}</div>
        <div class="card-sub neutral">across {n_months} months</div>
    </div>
    <div class="card card-accent">
        <div class="card-label">This Month</div>
        <div class="card-value">${this_month_amt:,.0f}</div>
        <div class="card-sub {delta_class}">{delta_arrow} ${abs(mom_delta):,.0f} vs last month</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Monthly spend chart ──────────────────────────────────────────────────────────
monthly = (
    df.groupby("YearMonth")["Amount"]
    .sum().reset_index()
    .rename(columns={"Amount": "Total"})
    .sort_values("YearMonth")
)
monthly["Month"] = monthly["YearMonth"].astype(str)

fig_monthly = go.Figure()
fig_monthly.add_trace(go.Bar(
    x=monthly["Month"], y=monthly["Total"],
    marker_color=ACCENT, marker_opacity=0.85,
    name="Spend",
    hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
))
fig_monthly.add_trace(go.Scatter(
    x=monthly["Month"], y=[avg_monthly] * len(monthly),
    mode="lines",
    line=dict(color="#94A3B8", width=1.5, dash="dash"),
    name="Average",
    hovertemplate="Avg: $%{y:,.0f}<extra></extra>",
))
fig_monthly.update_layout(
    plot_bgcolor="white", paper_bgcolor="white",
    height=280, margin=dict(l=0, r=0, t=10, b=0),
    bargap=0.3,
    xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#64748B")),
    yaxis=dict(showgrid=True, gridcolor="#F1F5F9",
               tickprefix="$", tickformat=",.0f",
               tickfont=dict(size=11, color="#64748B")),
    legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                font=dict(size=12, color="#64748B")),
)

st.markdown("<div class='section-title'>Monthly Spend</div>", unsafe_allow_html=True)
st.plotly_chart(fig_monthly, use_container_width=True)

# ── Category breakdown ───────────────────────────────────────────────────────────
cat = (
    df.groupby("Category")["Amount"].sum()
    .sort_values(ascending=False)
    .reset_index().rename(columns={"Amount": "Total"})
)
cat["Pct"] = cat["Total"] / cat["Total"].sum() * 100

TOP_N     = 6
top_cats  = cat.head(TOP_N).copy()
other_amt = cat.iloc[TOP_N:]["Total"].sum()
if other_amt > 0:
    top_cats = pd.concat([
        top_cats,
        pd.DataFrame([{"Category": "Other", "Total": other_amt,
                        "Pct": cat.iloc[TOP_N:]["Pct"].sum()}])
    ], ignore_index=True)

segments_html = ""
legend_html   = ""
for i, row in top_cats.iterrows():
    color = CAT_COLORS[i % len(CAT_COLORS)]
    segments_html += (
        f'<div style="width:{row["Pct"]:.1f}%;background:{color};height:100%;"></div>'
    )
    legend_html += f"""
    <div style="display:flex;flex-direction:column;min-width:110px;">
        <div style="display:flex;align-items:center;gap:6px;">
            <div style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></div>
            <span style="font-size:12px;color:#64748B;white-space:nowrap;overflow:hidden;
                         text-overflow:ellipsis;max-width:100px;">{row["Category"]}</span>
        </div>
        <div style="font-size:18px;font-weight:700;color:#0F172A;margin-top:4px;">
            ${row["Total"]:,.0f}
        </div>
        <div style="font-size:11px;color:#94A3B8;">{row["Pct"]:.1f}%</div>
    </div>"""

st.markdown("<div class='section-title'>Spending by Category</div>", unsafe_allow_html=True)
st.markdown(f"""
<div class="card" style="margin-bottom:24px;">
    <div style="display:flex;height:8px;border-radius:6px;overflow:hidden;
                margin-bottom:20px;gap:2px;">
        {segments_html}
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:20px;">
        {legend_html}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Explore ──────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Explore</div>", unsafe_allow_html=True)


def chart_layout():
    return dict(plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0, r=0, t=10, b=0))


# Categories detail
with st.expander("Categories — Full Breakdown"):
    other_threshold = st.slider("Group categories below this % into 'Other'",
                                0, 10, 1, key="cat_thresh")
    cat_full = (
        df.groupby("Category")["Amount"]
        .agg(["sum","count"])
        .rename(columns={"sum":"Total","count":"Transactions"})
        .sort_values("Total", ascending=False)
        .reset_index()
    )
    cat_full["% of Spend"] = (cat_full["Total"] / cat_full["Total"].sum() * 100).round(1)
    small = cat_full[cat_full["% of Spend"] < other_threshold]
    if not small.empty and other_threshold > 0:
        cat_full = pd.concat([
            cat_full[cat_full["% of Spend"] >= other_threshold],
            pd.DataFrame([{"Category":"Other","Total":small["Total"].sum(),
                           "Transactions":small["Transactions"].sum(),
                           "% of Spend":small["% of Spend"].sum().round(1)}])
        ], ignore_index=True).sort_values("Total", ascending=False).reset_index(drop=True)

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(cat_full, x="Total", y="Category", orientation="h",
                     labels={"Total":"Spend ($)","Category":""},
                     color_discrete_sequence=[ACCENT])
        fig.update_layout(**chart_layout(),
                          yaxis={"categoryorder":"total ascending"},
                          xaxis_tickprefix="$", xaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig2 = px.pie(cat_full, values="Total", names="Category", hole=0.45,
                      color_discrete_sequence=CAT_COLORS)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(**chart_layout(), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    cat_time = (
        df[df["Category"].isin(cat_full["Category"].head(6).tolist())]
        .groupby(["YearMonth","Category"])["Amount"].sum().reset_index()
    )
    cat_time["Month"] = cat_time["YearMonth"].astype(str)
    fig3 = px.area(cat_time, x="Month", y="Amount", color="Category",
                   labels={"Amount":"Spend ($)","Month":""},
                   color_discrete_sequence=CAT_COLORS)
    fig3.update_layout(**chart_layout(),
                       yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(cat_full.style.format({"Total":"${:,.2f}","% of Spend":"{:.1f}%"}),
                 use_container_width=True, hide_index=True)

# Top Merchants
with st.expander("Top Merchants"):
    top_n = st.slider("Number of merchants", 10, 50, 20, key="merch_n")
    merchants = (
        df.groupby("Description")["Amount"]
        .agg(["sum","count","mean"])
        .rename(columns={"sum":"Total","count":"Visits","mean":"Avg per Visit"})
        .sort_values("Total", ascending=False).head(top_n)
        .reset_index().rename(columns={"Description":"Merchant"})
    )
    fig4 = px.bar(merchants, x="Total", y="Merchant", orientation="h",
                  labels={"Total":"Spend ($)","Merchant":""},
                  hover_data={"Visits":True,"Avg per Visit":":.2f"},
                  color_discrete_sequence=[ACCENT])
    fig4.update_layout(**chart_layout(),
                       yaxis={"categoryorder":"total ascending"},
                       xaxis_tickprefix="$", xaxis_tickformat=",.0f",
                       height=max(400, top_n * 28))
    st.plotly_chart(fig4, use_container_width=True)
    st.dataframe(merchants.style.format({"Total":"${:,.2f}","Avg per Visit":"${:,.2f}"}),
                 use_container_width=True, hide_index=True)

# Merchant Search
with st.expander("Merchant Search"):
    query = st.text_input("Search merchant name",
                          placeholder="e.g. Amazon, Delta, Whole Foods", key="search_q")
    if not query:
        st.info("Type a merchant name to see all matching transactions.")
    else:
        results = df[df["Description"].str.contains(query, case=False, na=False)].copy()
        if results.empty:
            st.warning(f'No transactions found matching "{query}".')
        else:
            matched = results["Description"].unique()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Spent",   f"${results['Amount'].sum():,.2f}")
            c2.metric("Transactions",  f"{len(results):,}")
            c3.metric("Avg per Visit", f"${results['Amount'].mean():,.2f}")
            c4.metric("Date Range",
                      f"{results['Date'].min().date()} → {results['Date'].max().date()}")
            if len(matched) > 1:
                st.caption(f"Matching: {', '.join(matched)}")
            ot = (
                results.groupby("YearMonth")["Amount"]
                .sum().reset_index().sort_values("YearMonth")
            )
            ot["Month"] = ot["YearMonth"].astype(str)
            fig5 = px.bar(ot, x="Month", y="Amount",
                          labels={"Amount":"Spend ($)","Month":""},
                          color_discrete_sequence=[ACCENT])
            fig5.update_layout(**chart_layout(),
                               yaxis_tickprefix="$", yaxis_tickformat=",.0f")
            st.plotly_chart(fig5, use_container_width=True)
            st.dataframe(
                results[["Date","Description","Category","Amount","Card"]]
                .sort_values("Date", ascending=False)
                .style.format({"Amount":"${:,.2f}",
                               "Date": lambda d: d.strftime("%Y-%m-%d")}),
                use_container_width=True, hide_index=True,
            )

# Subscriptions
with st.expander("Subscriptions"):
    def detect_subscriptions(df, min_occurrences=2):
        results = []
        for merchant, group in df.groupby("Description"):
            if len(group) < min_occurrences:
                continue
            dates   = group["Date"].sort_values().reset_index(drop=True)
            amounts = group["Amount"]
            gaps    = dates.diff().dropna().dt.days
            if len(gaps) == 0:
                continue
            avg_gap = gaps.mean()
            std_gap = gaps.std() if len(gaps) > 1 else 0
            if   5   <= avg_gap <= 9   and std_gap <= 2:  cadence, me = "Weekly",    amounts.mean() * 4.33
            elif 25  <= avg_gap <= 35  and std_gap <= 5:  cadence, me = "Monthly",   amounts.mean()
            elif 85  <= avg_gap <= 95  and std_gap <= 7:  cadence, me = "Quarterly", amounts.mean() / 3
            elif 355 <= avg_gap <= 375 and std_gap <= 10: cadence, me = "Annual",    amounts.mean() / 12
            else: continue
            if (amounts.std() / amounts.mean() if amounts.mean() > 0 else 1) > 0.15:
                continue
            results.append({"Merchant": merchant, "Cadence": cadence,
                             "Occurrences": len(group), "Avg Charge": amounts.mean(),
                             "Est Monthly Cost": me,
                             "First Seen": dates.iloc[0].date(),
                             "Last Seen":  dates.iloc[-1].date()})
        return (pd.DataFrame(results)
                .sort_values("Est Monthly Cost", ascending=False)
                .reset_index(drop=True))

    subs = detect_subscriptions(df)
    if subs.empty:
        st.info("No subscriptions detected. Works best with 3+ months of data.")
    else:
        monthly_sub = subs["Est Monthly Cost"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Detected Subscriptions", len(subs))
        c2.metric("Est. Monthly Cost", f"${monthly_sub:,.2f}",
                  f"${monthly_sub * 12:,.2f} / yr")
        fig6 = px.bar(subs, x="Est Monthly Cost", y="Merchant", orientation="h",
                      color="Cadence", color_discrete_sequence=CAT_COLORS,
                      labels={"Est Monthly Cost":"Est. Monthly ($)","Merchant":""})
        fig6.update_layout(**chart_layout(),
                           yaxis={"categoryorder":"total ascending"},
                           xaxis_tickprefix="$", xaxis_tickformat=",.2f")
        st.plotly_chart(fig6, use_container_width=True)
        st.dataframe(subs.style.format({"Avg Charge":"${:,.2f}","Est Monthly Cost":"${:,.2f}"}),
                     use_container_width=True, hide_index=True)

# Large Transactions
with st.expander("Large Transactions"):
    percentile = st.slider("Flag transactions in the top X% by amount",
                           1, 25, 5, key="large_pct")
    threshold  = df["Amount"].quantile(1 - percentile / 100)
    large = (df[df["Amount"] >= threshold]
             .sort_values("Amount", ascending=False)
             .reset_index(drop=True))
    c1, c2, c3 = st.columns(3)
    c1.metric("Threshold",             f"${threshold:,.2f}")
    c2.metric("Flagged Transactions",  f"{len(large):,}")
    c3.metric("Total Flagged Spend",   f"${large['Amount'].sum():,.2f}")
    fig7 = px.scatter(large, x="Date", y="Amount", color="Category",
                      hover_data={"Description":True,"Card":True},
                      labels={"Amount":"Amount ($)"},
                      color_discrete_sequence=CAT_COLORS)
    fig7.update_layout(**chart_layout(),
                       yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    fig7.update_traces(marker=dict(size=10, opacity=0.8))
    st.plotly_chart(fig7, use_container_width=True)
    st.dataframe(
        large[["Date","Description","Category","Amount","Card"]]
        .style.format({"Amount":"${:,.2f}",
                       "Date": lambda d: d.strftime("%Y-%m-%d")}),
        use_container_width=True, hide_index=True,
    )
