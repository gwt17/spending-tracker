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

## Dashboard sections
- **Summary metrics** — total spend, avg monthly, biggest month, latest month
- **Monthly** — bar chart, cumulative line, month-over-month delta
- **Categories** — bar + pie chart, stacked area over time, "Other" threshold slider
- **Merchants** — top N merchants by total spend (adjustable slider)
- **Subscriptions** — heuristic detection by cadence (weekly/monthly/quarterly/annual)

## What's planned next
- Merchant search/filter
- Flag unusually large transactions
- Automate monthly CSV merging workflow
