# Spending Tracker — Claude Context

## What this is
A personal finance dashboard for tracking credit card and checking account spending.
The user exports CSVs from their accounts; the app visualizes trends, categories,
merchants, and subscriptions.

## Stack
- **Python** with a `.venv` virtual environment
- **Streamlit** — main dashboard (multipage, runs in browser)
- **pandas** — data processing
- **plotly** — interactive charts
- **pytest** — unit tests in `tests/`
- **Jupyter notebook** — scratchpad for one-off exploration

## Directory structure
```
Spending_Tracker/
├── data/                         # Raw CSV exports + merged.csv (gitignored)
├── notebooks/
│   └── spending_analysis.ipynb   # Exploratory notebook (not the main tool)
├── pages/
│   ├── 1_Categories.py           # Category breakdown + bar chart
│   ├── 2_Merchants.py            # Top merchants + search
│   ├── 3_Subscriptions.py        # Subscription detection
│   └── 5_Transactions.py         # Full transaction list + transfer exclusions
├── tests/
│   └── test_utils.py             # Unit tests for utils.py business logic
├── .streamlit/
│   └── config.toml               # Streamlit theme (light mode)
├── app.py                        # Main dashboard (overview + navigation)
├── utils.py                      # Shared constants, loaders, CSS, helpers
├── merge.py                      # Merges + deduplicates all CSVs in data/
├── launch.command                # Mac: double-click to launch the app
├── requirements.txt
├── .gitignore
└── CLAUDE.md
```

## Data sources

### Credit cards (Chase format)
CSV columns: `Transaction Date, Post Date, Description, Category, Type, Amount`
- Negative Amount = expense, positive = payment/credit
- Filtered to expenses only; Amount flipped to positive

### Checking account (Chase checking format)
CSV columns: `Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #`
- Credits → `income`, Debits → `expense`
- Transfers (Schwab, Vanguard, etc.) → `transfer` (excluded from spend totals)

### RecordType column
Every row in the merged dataset has `RecordType`: `"expense"`, `"income"`, or `"transfer"`.
- Only `expense` rows appear in spend calculations and charts.
- `income` rows are shown in green on the Transactions page.
- `transfer` rows are excluded entirely, shown in the "Excluded transfers" expander.

### CARD_CONFIG
Defined at the top of both `utils.py` and `merge.py` — maps CSV filename patterns to
column layouts. **Keep in sync manually** (merge.py runs standalone, can't import utils).

### TRANSFER_KEYWORDS
Defined in both `utils.py` and `merge.py`. Case-insensitive substring match against
Description. Matching checking-account rows are classified as `transfer`.
Current list: schwab, moneylink, fidelity, vanguard, tdameritrade, e*trade, etrade,
robinhood, coinbase, wealthfront, betterment, acorns, stash invest.
**Keep in sync manually** between both files.

## Workflow
1. Export CSVs from credit card/bank websites, drop into `data/`
2. Run `python merge.py` — merges, deduplicates, classifies transfers, saves `data/merged.csv`
3. Launch the app — reads `merged.csv` if it exists, otherwise reads CSVs directly

**Launching:**
- Mac: double-click `launch.command`, or run `streamlit run app.py`
- Windows: activate `.venv` then run `streamlit run app.py`

**After re-running merge.py:** click ↺ Reload on any page to clear the Streamlit data cache.

## Deduplication logic
`merge.py` handles overlapping CSV exports (e.g. Jan–Jun and Apr–Dec).
A transaction is a duplicate only if it matches on Date, Description, Amount, Card,
and sequence number. The sequence number preserves legitimate same-day same-amount
charges at the same merchant.

## Architecture

### utils.py — shared module
- **Constants:** `ACCENT`, `CAT_COLORS`, `CARD_CONFIG`, `TRANSFER_KEYWORDS`, `DATA_DIR`
- **`load_all()`** — reads merged.csv (or all CSVs), returns cleaned DataFrame; `@st.cache_data`
- **`date_filter(df, key, default_preset)`** — renders preset dropdown + card selector; returns `(start, end, selected_card)`
- **`inject_global_css()`** — injects full CSS block (fonts, cards, section titles, buttons, etc.)
- **`compute_insights(df)`** — compares current month vs 3-month baseline per category; returns top-5 insight dicts
- **`detect_subscriptions(df)`** — heuristic detection of recurring charges by cadence

### app.py — main dashboard
Uses `st.navigation()` multipage pattern. The main page is wrapped in a `dashboard()` function.

**Layout (top to bottom):**
1. Blue gradient banner — "Spending Dashboard"
2. `date_filter()` — preset dropdown (Last 3 months default) + card selector
3. Hero metrics (3 cards) — This Month spend, MoM delta, 3-month average
4. Insights row — category spikes/drops vs 3-month avg (hidden if < 2 months of data)
5. Monthly Spend — bar chart with dashed average line
6. Spending by Category — stacked bar + color-coded category cards with trend arrows

**Navigation (sidebar):**
- Dashboard (main)
- Transactions
- Categories
- Merchants
- Subscriptions

### Detail pages
All detail pages:
- Call `load_all()` directly (not session_state) so they always show fresh data
- Include a ↺ Reload button to clear cache
- Filter to `RecordType == "expense"` (except Transactions which shows all)
- Use custom HTML metric cards (not `st.metric()`) to guarantee color fidelity

## Design system
- **Theme:** Light background (#F0F4FA), deep blue accent (#1B3A6B), white cards
- **Fonts:** DM Sans (labels/body), DM Mono (numbers) — loaded from Google Fonts
- **CSS:** All injected via `inject_global_css()` in utils.py
- **Metric cards:** Custom HTML with explicit inline colors (never `st.metric()`)
- **Category colors:** `CAT_COLORS` list in utils.py
- **Section titles:** Left 3px blue border accent via `.section-title` class
- **Buttons:** White bg, #1B3A6B text, light border — `button[data-testid="baseButton-secondary"]`

## Tests
Run with: `python -m pytest tests/ -v`
- `TestGetConfig` — card config lookup (exact, substring, unknown, default)
- `TestLoadChecking` — checking CSV parsing (income, expense, transfer classification, autopay exclusion)

## What's planned next
- Automate monthly CSV merging workflow
- Add more transfer keywords as new accounts are added
