import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Spending Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

    # Keep expenses only
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
    st.error(
        "No CSV files found in the `data/` folder. "
        "Drop your Chase export there and click **Reload Data**."
    )
    if st.button("Reload Data"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# ── Sidebar filters ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filters")

    cards = ["All"] + sorted(df_all["Card"].unique().tolist())
    selected_card = st.selectbox("Card", cards)

    min_date = df_all["Date"].min().date()
    max_date = df_all["Date"].max().date()
    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    all_cats = sorted(df_all["Category"].unique().tolist())
    selected_cats = st.multiselect("Categories", all_cats, default=all_cats)

    st.markdown("---")
    if st.button("Reload Data"):
        st.cache_data.clear()
        st.rerun()

# ── Apply filters ───────────────────────────────────────────────────────────────
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

# ── Summary metrics ─────────────────────────────────────────────────────────────
st.title("💳 Spending Tracker")

monthly_totals  = df.groupby("YearMonth")["Amount"].sum()
total_spend     = df["Amount"].sum()
n_months        = df["YearMonth"].nunique()
avg_monthly     = total_spend / n_months if n_months else 0
biggest_month   = monthly_totals.idxmax()
biggest_amt     = monthly_totals.max()
current_period  = df["YearMonth"].max()
this_month_amt  = monthly_totals.get(current_period, 0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Spend",   f"${total_spend:,.2f}")
c2.metric("Avg Monthly",   f"${avg_monthly:,.2f}")
c3.metric("Biggest Month", f"${biggest_amt:,.2f}", str(biggest_month))
c4.metric("Latest Month",  f"${this_month_amt:,.2f}", str(current_period))

st.markdown("---")

# ── Tabs ────────────────────────────────────────────────────────────────────────
tab_monthly, tab_cats, tab_merchants, tab_subs = st.tabs([
    "📅 Monthly", "🏷️ Categories", "🏪 Merchants", "🔁 Subscriptions"
])

# ── Monthly ─────────────────────────────────────────────────────────────────────
with tab_monthly:
    monthly = (
        df.groupby("YearMonth")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Total"})
        .sort_values("YearMonth")
    )
    monthly["Month"]      = monthly["YearMonth"].astype(str)
    monthly["Cumulative"] = monthly["Total"].cumsum()
    monthly["MoM Delta"]  = monthly["Total"].diff()

    col_a, col_b = st.columns(2)

    with col_a:
        fig = px.bar(
            monthly, x="Month", y="Total",
            title="Monthly Spend",
            labels={"Total": "Spend ($)", "Month": ""},
            text_auto=".2s",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = px.line(
            monthly, x="Month", y="Cumulative",
            title="Cumulative Spend",
            labels={"Cumulative": "Spend ($)", "Month": ""},
            markers=True,
        )
        fig2.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig2, use_container_width=True)

    delta = monthly.dropna(subset=["MoM Delta"])
    fig3 = px.bar(
        delta, x="Month", y="MoM Delta",
        title="Month-over-Month Change  (red = more spending, green = less)",
        labels={"MoM Delta": "Change ($)", "Month": ""},
        color="MoM Delta",
        color_continuous_scale=["#2ca02c", "#ffffff", "#d62728"],
        color_continuous_midpoint=0,
    )
    fig3.update_layout(
        yaxis_tickprefix="$", yaxis_tickformat=",.0f",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(
        monthly[["Month", "Total", "Cumulative", "MoM Delta"]].style.format(
            {"Total": "${:,.2f}", "Cumulative": "${:,.2f}", "MoM Delta": "${:,.2f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

# ── Categories ──────────────────────────────────────────────────────────────────
with tab_cats:
    other_threshold = st.slider("Group categories below this % into 'Other'", 0, 10, 1)

    cat = (
        df.groupby("Category")["Amount"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "Total", "count": "Transactions"})
        .sort_values("Total", ascending=False)
        .reset_index()
    )
    cat["% of Spend"] = (cat["Total"] / cat["Total"].sum() * 100).round(1)

    # Consolidate small categories into "Other"
    small = cat[cat["% of Spend"] < other_threshold]
    if not small.empty and other_threshold > 0:
        other_row = pd.DataFrame([{
            "Category":     "Other",
            "Total":        small["Total"].sum(),
            "Transactions": small["Transactions"].sum(),
            "% of Spend":   small["% of Spend"].sum().round(1),
        }])
        cat = pd.concat(
            [cat[cat["% of Spend"] >= other_threshold], other_row],
            ignore_index=True,
        ).sort_values("Total", ascending=False).reset_index(drop=True)

    col_a, col_b = st.columns(2)

    with col_a:
        fig = px.bar(
            cat, x="Total", y="Category", orientation="h",
            title="Spend by Category",
            labels={"Total": "Spend ($)", "Category": ""},
            text_auto=".2s",
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_tickprefix="$", xaxis_tickformat=",.0f",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = px.pie(
            cat, values="Total", names="Category",
            title="Category Share", hole=0.4,
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig2, use_container_width=True)

    # Category over time
    top_cats = cat["Category"].head(6).tolist()
    cat_time = (
        df[df["Category"].isin(top_cats)]
        .groupby(["YearMonth", "Category"])["Amount"]
        .sum()
        .reset_index()
    )
    cat_time["Month"] = cat_time["YearMonth"].astype(str)
    fig3 = px.area(
        cat_time, x="Month", y="Amount", color="Category",
        title="Top Category Spend Over Time",
        labels={"Amount": "Spend ($)", "Month": ""},
    )
    fig3.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(
        cat.style.format({"Total": "${:,.2f}", "% of Spend": "{:.1f}%"}),
        use_container_width=True,
        hide_index=True,
    )

# ── Merchants ───────────────────────────────────────────────────────────────────
with tab_merchants:
    top_n = st.slider("Number of merchants to show", 10, 50, 20)

    merchants = (
        df.groupby("Description")["Amount"]
        .agg(["sum", "count", "mean"])
        .rename(columns={"sum": "Total", "count": "Visits", "mean": "Avg per Visit"})
        .sort_values("Total", ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={"Description": "Merchant"})
    )

    fig = px.bar(
        merchants, x="Total", y="Merchant", orientation="h",
        title=f"Top {top_n} Merchants by Total Spend",
        labels={"Total": "Spend ($)", "Merchant": ""},
        hover_data={"Visits": True, "Avg per Visit": ":.2f"},
        text_auto=".2s",
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_tickprefix="$", xaxis_tickformat=",.0f",
        height=max(400, top_n * 28),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        merchants.style.format({"Total": "${:,.2f}", "Avg per Visit": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

# ── Subscriptions ───────────────────────────────────────────────────────────────
with tab_subs:
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

            if   5   <= avg_gap <= 9   and std_gap <= 2:  cadence, monthly_est = "Weekly",    amounts.mean() * 4.33
            elif 25  <= avg_gap <= 35  and std_gap <= 5:  cadence, monthly_est = "Monthly",   amounts.mean()
            elif 85  <= avg_gap <= 95  and std_gap <= 7:  cadence, monthly_est = "Quarterly", amounts.mean() / 3
            elif 355 <= avg_gap <= 375 and std_gap <= 10: cadence, monthly_est = "Annual",    amounts.mean() / 12
            else:
                continue

            cv = amounts.std() / amounts.mean() if amounts.mean() > 0 else 1
            if cv > 0.15:
                continue

            results.append({
                "Merchant":         merchant,
                "Cadence":          cadence,
                "Occurrences":      len(group),
                "Avg Charge":       amounts.mean(),
                "Est Monthly Cost": monthly_est,
                "First Seen":       dates.iloc[0].date(),
                "Last Seen":        dates.iloc[-1].date(),
            })

        return (
            pd.DataFrame(results)
            .sort_values("Est Monthly Cost", ascending=False)
            .reset_index(drop=True)
        )

    subs = detect_subscriptions(df)

    if subs.empty:
        st.info(
            "No subscriptions detected. "
            "The heuristic works best with 3+ months of data and consistent charge amounts."
        )
    else:
        monthly_sub_total = subs["Est Monthly Cost"].sum()

        c1, c2 = st.columns(2)
        c1.metric("Detected Subscriptions", len(subs))
        c2.metric(
            "Est. Monthly Sub Cost", f"${monthly_sub_total:,.2f}",
            f"${monthly_sub_total * 12:,.2f} / yr"
        )

        fig = px.bar(
            subs, x="Est Monthly Cost", y="Merchant", orientation="h",
            color="Cadence",
            title="Subscriptions — Estimated Monthly Cost",
            labels={"Est Monthly Cost": "Est. Monthly Cost ($)", "Merchant": ""},
            hover_data={"Occurrences": True, "Avg Charge": ":.2f"},
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_tickprefix="$", xaxis_tickformat=",.2f",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            subs.style.format({"Avg Charge": "${:,.2f}", "Est Monthly Cost": "${:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
