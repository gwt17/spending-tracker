"""Shared constants, data loaders, and helpers for the Spending Tracker app."""

import re
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Theme ─────────────────────────────────────────────────────────────────────
ACCENT = "#1B3A6B"
CAT_COLORS = [
    "#1B3A6B", "#2563EB", "#0EA5E9", "#06B6D4",
    "#8B5CF6", "#EC4899", "#F59E0B", "#10B981",
]

# ── Card format config ────────────────────────────────────────────────────────
# Add an entry here for each CSV filename in data/ (key = filename without
# extension, lowercase). If no match is found, "default" (Chase format) is used.
#
# amount_sign: -1 if negative = expense (Chase), 1 if positive = expense
CARD_CONFIG = {
    "default": {                        # Chase credit card (standard)
        "date_col":    "Transaction Date",
        "desc_col":    "Description",
        "cat_col":     "Category",
        "amount_col":  "Amount",
        "amount_sign": -1,              # negative = expense
        "is_checking": False,
    },
    "checking": {                       # Chase checking — matches any filename containing "checking"
        "date_col":    "Posting Date",
        "desc_col":    "Description",
        "cat_col":     None,            # no category column
        "amount_col":  "Amount",
        "amount_sign": 1,               # positive = credit (income), negative = debit (expense)
        "is_checking": True,
        "details_col": "Details",       # "Credit" or "Debit"
    },
}

# Keywords that identify a CC payment coming out of checking (safe to exclude —
# they're already captured as individual charges in the credit card CSV).
CC_PAYMENT_KEYWORDS = ["autopay", "payment thank you", "online payment"]

# Keywords that identify investment/brokerage transfers — neither income nor expenses.
# These are excluded from all spending and income calculations.
# Add more here as needed (case-insensitive substring match on Description).
TRANSFER_KEYWORDS = [
    "schwab", "moneylink", "fidelity", "vanguard", "tdameritrade",
    "e*trade", "etrade", "robinhood", "coinbase", "wealthfront",
    "betterment", "acorns", "stash invest",
]

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"


# ── Merchant name cleanup ─────────────────────────────────────────────────────
def clean_merchant(name: str) -> str:
    """Strip Chase-style location codes and noise from merchant names."""
    # Remove #NNNN location codes
    name = re.sub(r'\s*#\d+', '', name)
    # Remove trailing standalone numbers of 4+ digits (store numbers, etc.)
    name = re.sub(r'\s+\d{4,}$', '', name)
    # Remove trailing city/state noise (all-caps 2-letter state at end)
    name = re.sub(r'\s+[A-Z]{2}$', '', name)
    name = name.strip()
    # Title-case only if the name is all-caps (Chase style)
    if name.isupper():
        name = name.title()
    return name


# ── Data loading ──────────────────────────────────────────────────────────────
def _get_config(card_key: str) -> dict:
    """Return the right CARD_CONFIG entry for a given file stem."""
    if card_key in CARD_CONFIG:
        return CARD_CONFIG[card_key]
    for key, cfg in CARD_CONFIG.items():
        if key != "default" and key in card_key:
            return cfg
    return CARD_CONFIG["default"]


def _load_checking(raw: pd.DataFrame, card_name: str, cfg: dict) -> pd.DataFrame:
    """Parse a Chase checking CSV into income + expense rows."""
    details_col = cfg.get("details_col", "Details")
    rows = []
    for _, r in raw.iterrows():
        desc       = str(r[cfg["desc_col"]]).strip()
        amount_raw = float(r[cfg["amount_col"]])
        details    = str(r.get(details_col, "")).strip().title()  # "Credit" or "Debit"
        is_credit  = details == "Credit" or amount_raw > 0

        if not is_credit and any(kw in desc.lower() for kw in CC_PAYMENT_KEYWORDS):
            continue  # Skip — already counted in credit card CSV

        desc_lower = desc.lower()
        is_transfer = any(kw in desc_lower for kw in TRANSFER_KEYWORDS)
        if is_transfer:
            record_type = "transfer"
            category    = "Transfer"
        elif is_credit:
            record_type = "income"
            category    = "Income"
        else:
            record_type = "expense"
            category    = "Uncategorized"

        rows.append({
            "Date":        pd.to_datetime(r[cfg["date_col"]]),
            "Description": desc,
            "Category":    category,
            "Amount":      abs(amount_raw),
            "Card":        card_name,
            "RecordType":  record_type,
        })

    if not rows:
        return pd.DataFrame(columns=["Date", "Description", "Category", "Amount", "Card", "RecordType"])
    return pd.DataFrame(rows)


def load_card(path: Path) -> pd.DataFrame:
    card_key = path.stem.lower()
    cfg = _get_config(card_key)
    raw = pd.read_csv(path, index_col=False)
    raw.columns = raw.columns.str.strip()

    if cfg.get("is_checking"):
        return _load_checking(raw, path.stem.title(), cfg)

    # Standard credit card path
    df = pd.DataFrame()
    df["Date"]        = pd.to_datetime(raw[cfg["date_col"]])
    df["Description"] = raw[cfg["desc_col"]].str.strip()
    df["Category"]    = (
        raw[cfg["cat_col"]].str.strip()
        if cfg["cat_col"] in raw.columns
        else "Uncategorized"
    )
    df["Amount"]      = raw[cfg["amount_col"]] * cfg["amount_sign"]
    df["Card"]        = path.stem.title()
    df["RecordType"]  = "expense"
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
    df["YearMonth"]   = df["Date"].dt.to_period("M")
    df["Description"] = df["Description"].apply(clean_merchant)
    # Backward-compat: existing merged.csv won't have RecordType
    if "RecordType" not in df.columns:
        df["RecordType"] = "expense"
    return df


# ── Date range logic (pure, testable — no Streamlit) ─────────────────────────
def _months_back(d: "datetime.date", n: int) -> "datetime.date":
    """First day of the month n months before d's month."""
    import datetime
    month = d.month - n
    year  = d.year + month // 12
    month = month % 12 or 12
    # floor-divide gives wrong result when month lands exactly on 0
    if d.month - n <= 0:
        year  = d.year - ((-( d.month - n) // 12) + 1)
        month = 12 - (-(d.month - n) % 12)
    return datetime.date(year, month, 1)


def compute_date_range(
    choice: str,
    today: "datetime.date",
    min_date: "datetime.date",
    max_date: "datetime.date",
) -> tuple:
    """Return (start, end) for a named preset. Pure function — no Streamlit."""
    import datetime

    # Rolling periods end at the later of today or max_date in data
    eff_end = min(today, max_date) if today <= max_date else max_date

    if choice == "Last month":
        first_this_month  = today.replace(day=1)
        last_of_last_month  = first_this_month - datetime.timedelta(days=1)
        first_of_last_month = last_of_last_month.replace(day=1)
        start = max(first_of_last_month, min_date)
        end   = min(last_of_last_month, max_date)
    elif choice == "Last 3 months":
        start = max(_months_back(today, 3), min_date)
        end   = eff_end
    elif choice == "Last 6 months":
        start = max(_months_back(today, 6), min_date)
        end   = eff_end
    elif choice == "YTD":
        start = max(datetime.date(today.year, 1, 1), min_date)
        end   = eff_end
    elif choice == "All time":
        start, end = min_date, max_date
    else:  # "Last 12 months" (default)
        start = max(_months_back(today, 12), min_date)
        end   = eff_end

    return start, end


# ── Date filter widget (Streamlit UI wrapper) ─────────────────────────────────
DATE_PRESETS = [
    "Last 12 months",
    "Last month",
    "Last 3 months",
    "Last 6 months",
    "YTD",
    "All time",
    "Custom",
]


def date_filter(df: pd.DataFrame, key: str = "date", default_preset: str = "Last 12 months") -> tuple:
    """Compact preset date dropdown. Returns (start_date, end_date, card)."""
    import datetime

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    today    = datetime.date.today()

    default_index = DATE_PRESETS.index(default_preset) if default_preset in DATE_PRESETS else 0

    col_preset, col_card = st.columns([2, 1.5])
    with col_preset:
        choice = st.selectbox(
            "Date range", DATE_PRESETS, index=default_index,
            label_visibility="collapsed", key=f"{key}_preset",
        )
    with col_card:
        all_cards = ["All cards"] + sorted(df["Card"].unique().tolist())
        selected_card = st.selectbox(
            "Card", all_cards,
            label_visibility="collapsed", key=f"{key}_card",
        )

    if choice == "Custom":
        dr = st.date_input(
            "Custom range",
            value=(min_date, max_date),
            min_value=min_date, max_value=max_date,
            label_visibility="collapsed", key=f"{key}_custom",
        )
        start, end = (dr[0], dr[1]) if len(dr) == 2 else (min_date, max_date)
    else:
        start, end = compute_date_range(choice, today, min_date, max_date)

    return start, end, selected_card


# ── Chart helpers ─────────────────────────────────────────────────────────────
def chart_layout(height=None):
    d = dict(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="DM Sans"),
    )
    if height:
        d["height"] = height
    return d


# ── Subscription detection ────────────────────────────────────────────────────
def detect_subscriptions(df: pd.DataFrame, min_occurrences: int = 2) -> pd.DataFrame:
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
        results.append({
            "Merchant": merchant, "Cadence": cadence,
            "Occurrences": len(group), "Avg Charge": amounts.mean(),
            "Est Monthly Cost": me,
            "First Seen": dates.iloc[0].date(),
            "Last Seen":  dates.iloc[-1].date(),
        })
    if not results:
        return pd.DataFrame()
    return (
        pd.DataFrame(results)
        .sort_values("Est Monthly Cost", ascending=False)
        .reset_index(drop=True)
    )


# ── Insights engine ───────────────────────────────────────────────────────────
def compute_insights(df: pd.DataFrame) -> list:
    if df.empty or df["YearMonth"].nunique() < 2:
        return []

    current_period   = df["YearMonth"].max()
    baseline_periods = sorted([p for p in df["YearMonth"].unique() if p < current_period])[-3:]
    if not baseline_periods:
        return []

    current_df  = df[df["YearMonth"] == current_period]
    baseline_df = df[df["YearMonth"].isin(baseline_periods)]
    current_by_cat  = current_df.groupby("Category")["Amount"].sum()
    baseline_by_cat = baseline_df.groupby("Category")["Amount"].sum() / len(baseline_periods)

    insights = []
    for cat in set(current_by_cat.index) | set(baseline_by_cat.index):
        this_month    = current_by_cat.get(cat, 0)
        baseline      = baseline_by_cat.get(cat, 0)
        dollar_change = this_month - baseline
        pct_change    = dollar_change / baseline if baseline > 0 else (1.0 if this_month > 0 else 0)
        if abs(pct_change) >= 0.20 and abs(dollar_change) >= 25:
            indicator = "spike" if dollar_change > 0 else "drop"
            insights.append({
                "type": "category", "category": cat,
                "headline": f"{cat} {'up' if indicator == 'spike' else 'down'} {abs(pct_change) * 100:.0f}% vs avg",
                "dollar_amount": this_month, "dollar_change": dollar_change,
                "pct_change": pct_change, "indicator": indicator,
            })

    # Top merchant this month
    if not current_df.empty:
        top = current_df.groupby("Description")["Amount"].sum().nlargest(1)
        if len(top) > 0:
            insights.append({
                "type": "merchant", "category": "Top Merchant",
                "headline": f"Top merchant: {top.index[0]}",
                "dollar_amount": top.iloc[0], "dollar_change": top.iloc[0],
                "pct_change": 0, "indicator": "info",
            })

    insights.sort(key=lambda x: abs(x["dollar_change"]), reverse=True)
    return insights[:5]


# ── Global CSS ────────────────────────────────────────────────────────────────
def inject_global_css(accent: str = ACCENT) -> None:
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700&display=swap');

html, body, .stApp {{
    background-color: #F0F4FA;
    background-image: radial-gradient(#1B3A6B14 1px, transparent 1px);
    background-size: 20px 20px;
    font-family: 'DM Sans', sans-serif;
    color: #0F172A;
}}
#MainMenu, footer, .stDeployButton {{ display: none !important; }}

:root {{
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.04);
    --shadow-md: 0 2px 8px rgba(27,58,107,0.08), 0 1px 3px rgba(27,58,107,0.05);
    --shadow-lg: 0 4px 16px rgba(27,58,107,0.10), 0 2px 6px rgba(0,0,0,0.05);
}}

/* Filter bar */
.filter-bar {{
    background: white;
    border-radius: 10px;
    padding: 14px 20px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 24px;
}}

/* Filter summary badge (detail pages) */
.filter-summary {{
    display: inline-block;
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 6px 14px;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: #475569;
    margin-bottom: 20px;
    box-shadow: var(--shadow-sm);
}}

/* Metric cards */
.card {{
    background: white;
    border-radius: 12px;
    padding: 22px 24px;
    box-shadow: var(--shadow-md);
    border: 1px solid rgba(27,58,107,0.07);
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s ease;
}}
.card::after {{
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {accent}, #2563EB);
    opacity: 0;
    transition: opacity 0.2s ease;
}}
.card:hover::after {{ opacity: 1; }}
.card:hover {{ box-shadow: var(--shadow-lg); }}
.card-label {{
    color: #94A3B8;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.card-value {{
    color: #0F172A;
    font-family: 'DM Mono', monospace;
    font-size: 32px;
    font-weight: 500;
    letter-spacing: -0.02em;
    margin-top: 8px;
    line-height: 1;
}}
.card-sub {{
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    margin-top: 6px;
    font-weight: 500;
}}
.up      {{ color: #DC2626; }}
.down    {{ color: #16A34A; }}
.neutral {{ color: #94A3B8; }}

/* Section titles */
.section-title {{
    color: #0F172A;
    font-family: 'DM Sans', sans-serif;
    font-size: 16px;
    font-weight: 700;
    margin: 28px 0 12px 0;
    padding-left: 12px;
    border-left: 3px solid {accent};
}}

/* Expanders */
[data-testid="stExpander"] {{
    background: white;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    margin-bottom: 8px;
}}
[data-testid="stExpander"] summary {{
    color: #1B3A6B !important;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 14px;
}}
[data-testid="stExpander"] summary p {{
    color: #1B3A6B !important;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
}}

/* Insight cards */
.insight-row {{
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 8px;
    margin-bottom: 8px;
}}
.insight-card {{
    background: white;
    border-radius: 10px;
    padding: 16px 18px;
    min-width: 200px;
    max-width: 240px;
    flex-shrink: 0;
    box-shadow: var(--shadow-sm);
    border: 1px solid #E2E8F0;
    position: relative;
    overflow: hidden;
}}
.insight-card.spike {{ border-top: 3px solid #DC2626; }}
.insight-card.drop  {{ border-top: 3px solid #16A34A; }}
.insight-card.info  {{ border-top: 3px solid {accent}; }}
.insight-icon {{
    font-size: 18px;
    margin-bottom: 6px;
}}
.insight-headline {{
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #0F172A;
    margin-bottom: 8px;
    line-height: 1.3;
}}
.insight-amount {{
    font-family: 'DM Mono', monospace;
    font-size: 22px;
    font-weight: 500;
    color: #0F172A;
    letter-spacing: -0.02em;
}}
.insight-delta {{
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    color: #64748B;
    margin-top: 4px;
}}

/* Reload / secondary buttons */
button[data-testid="baseButton-secondary"] {{
    background: white !important;
    color: #1B3A6B !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}}
button[data-testid="baseButton-secondary"]:hover {{
    background: #F1F5F9 !important;
    border-color: #1B3A6B !important;
}}

</style>
""", unsafe_allow_html=True)
