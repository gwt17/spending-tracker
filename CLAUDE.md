# Spending Tracker — Claude Context

## What this is
A personal finance dashboard for tracking credit card spending. The user exports CSVs
from their credit card accounts and the app visualizes spending trends, categories,
merchants, and subscriptions.

## Stack
- **Python** with a `.venv` virtual environment
- **Streamlit** — main dashboard (runs in browser)
- **pandas** — data processing
- **plotly** — interactive charts
- **Jupyter notebook** — kept as a scratchpad for one-off exploration

## Directory structure
```
Spending_Tracker/
├── data/                         # Raw CSV exports + merged.csv (gitignored)
├── notebooks/
│   └── spending_analysis.ipynb   # Exploratory notebook (not the main tool)
├── app.py                        # Main Streamlit dashboard
├── merge.py                      # Merges + deduplicates all CSVs in data/
├── launch.command                # Mac: double-click to launch the app
├── requirements.txt
├── .gitignore
└── CLAUDE.md
```

## Data format
Chase CSV columns: `Transaction Date, Post Date, Description, Category, Type, Amount`
- Negative Amount = expense, positive = payment/credit
- We filter to expenses only and flip Amount to positive

Multiple cards are supported. Each CSV filename becomes the card name in the app
(e.g. `chase_2024.csv` → "Chase 2024"). Card-specific column configs live in
`CARD_CONFIG` at the top of both `app.py` and `merge.py`.

## Workflow
1. Export CSVs from credit card websites, drop into `data/`
2. Run `python merge.py` — merges all CSVs, removes duplicates, saves `data/merged.csv`
3. Launch the app — reads from `merged.csv` if it exists, otherwise reads all CSVs directly

**Launching the app:**
- Mac: double-click `launch.command`, or run `streamlit run app.py`
- Windows: activate `.venv` then run `streamlit run app.py`

## Deduplication logic
`merge.py` handles overlapping CSV exports (e.g. Jan–Jun and Apr–Dec).
A transaction is a duplicate only if it appears across multiple files with the same
Date, Description, Amount, Card, and sequence number. The sequence number preserves
legitimate same-day same-amount charges at the same merchant.

## Dashboard design
**Theme:** Light background (#F0F4FA), deep blue accent (#1B3A6B), white cards.
Custom CSS injected via `st.markdown` at the top of `app.py`.

**Layout (top to bottom):**
1. **Blue gradient banner** — "Spending Dashboard" title with subtitle
2. **Hero metrics** — YTD spend, 12-month rolling, monthly average, this month (with MoM delta)
   - Rendered via `st.empty()` placeholder so they appear above the filters but compute after
3. **Filter bar** — horizontal row: Card selector, Date Range, Categories (multiselect,
   defaults to empty = all), Reload button
4. **Monthly Spend** — bar chart with dashed average line (plotly)
5. **Spending by Category** — plotly stacked bar + color-coded category cards
6. **Blue gradient Explore banner** — visually separates overview from detail sections
7. **Explore expanders** (collapsible):
   - Categories — Full Breakdown (bar, pie, area over time, Other threshold slider)
   - Top Merchants (adjustable top-N slider)
   - Merchant Search (partial name match, summary metrics, monthly chart, transaction table)
   - Subscriptions (heuristic: weekly/monthly/quarterly/annual cadence detection)
   - Large Transactions (top X% by amount, scatter plot over time)

**Design notes:**
- Section titles have a left blue border accent
- All charts use white plot/paper background
- Expanders styled with white background and blue header text
- Category colors: `CAT_COLORS` list defined at top of `app.py`

## What's planned next
- Automate monthly CSV merging workflow
- Any further UI refinements
