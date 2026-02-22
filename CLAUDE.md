# Spending Tracker — Claude Context

## What this is
A personal finance dashboard for tracking credit card and checking account spending,
savings, and investments. The user exports CSVs from their accounts; the app visualizes
trends, categories, merchants, subscriptions, transfers, and a full money summary with
savings rate.

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
├── data/                          # Raw CSV exports + merged.csv (gitignored)
│   ├── merged.csv                 # Output of merge.py (gitignored)
│   ├── overrides.csv              # Transaction exclusions/corrections (gitignored)
│   ├── transfer_keywords.csv      # Custom transfer classification keywords (gitignored)
│   └── finance_config.csv         # Manual 401k/HSA/ESPP contributions (gitignored)
├── notebooks/
│   └── spending_analysis.ipynb    # Exploratory notebook (not the main tool)
├── pages/
│   ├── 1_Categories.py            # Category breakdown — clickable table + bar chart + drilldown
│   ├── 2_Merchants.py             # Top merchants — clickable chart + table + drilldown
│   ├── 3_Subscriptions.py         # Subscription detection
│   ├── 4_Large_Transactions.py    # Large transaction explorer
│   ├── 5_Transactions.py          # Full transaction list (all RecordTypes)
│   ├── 6_Annual_Review.py         # Year-by-year analysis — monthly chart, categories, merchants
│   ├── 7_Exclusions.py            # Transaction overrides + custom transfer keywords
│   ├── 8_Transfers.py             # Investment/savings transfer activity
│   ├── 9_Money_Summary.py         # Full money picture — income, spend, savings rate, allocation
│   └── 10_Finance_Config.py       # Manual contribution entry (401k, HSA, ESPP, Roth IRA)
├── tests/
│   └── test_utils.py              # Unit tests for utils.py business logic
├── .streamlit/
│   └── config.toml                # Streamlit theme (light mode)
├── app.py                         # Main dashboard (overview + navigation)
├── utils.py                       # Shared constants, loaders, CSS, helpers
├── merge.py                       # Merges + deduplicates all CSVs in data/
├── launch.command                 # Mac: double-click to launch the app
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
- `transfer` rows feed the Transfers page and Money Summary.

### CARD_CONFIG
Defined at the top of both `utils.py` and `merge.py` — maps CSV filename patterns to
column layouts. **Keep in sync manually** (merge.py runs standalone, can't import utils).

### TRANSFER_KEYWORDS
Defined in both `utils.py` and `merge.py`. Case-insensitive substring match against
Description. Matching checking-account rows are classified as `transfer`.
**Keep in sync manually** between both files. Additional keywords can be added at runtime
via the Exclusions page (Manage → Overrides) without editing source code.

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
**Constants:** `ACCENT`, `CAT_COLORS`, `CARD_CONFIG`, `TRANSFER_KEYWORDS`, `DATA_DIR`

**Path constants:** `OVERRIDES_PATH`, `CUSTOM_KEYWORDS_PATH`, `FINANCE_CONFIG_PATH`

**Core loaders:**
- `load_all()` — reads merged.csv (or all CSVs), applies overrides + custom keywords,
  returns cleaned DataFrame; `@st.cache_data`
- `load_finance_config()` — reads `data/finance_config.csv`
- `load_overrides()` — reads `data/overrides.csv`
- `load_custom_keywords()` — reads `data/transfer_keywords.csv`

**Save helpers:**
- `save_override(date_str, description, original_amount, action, new_amount, new_category, notes)`
- `save_custom_keyword(keyword, notes)`
- `save_finance_config_entry(name, type_, amount_per_year, employer_match, notes)`

**UI helpers:**
- `date_filter(df, key, default_preset)` — renders preset dropdown + card selector
- `inject_global_css()` — injects full CSS block (fonts, cards, section titles, buttons)
- `render_drilldown(df, title)` — renders styled HTML transaction table with total row
- `compute_insights(df)` — compares current month vs 3-month baseline per category
- `detect_subscriptions(df)` — heuristic detection of recurring charges by cadence

**Override application in load_all():**
```python
# Per override row: exclude, override amount, or recategorize
if action == "exclude":   df = df[~mask]
if action == "override":  df.loc[mask, "Amount"] = new_amount
if action == "recategorize": df.loc[mask, "Category"] = new_category
# Then apply custom transfer keywords
df.loc[mask_kw, "RecordType"] = "transfer"
```

### app.py — main dashboard
Uses `st.navigation()` multipage pattern. Navigation sections:

| Section | Pages |
|---|---|
| Overview | Dashboard (main) |
| Review | Annual Review, Money Summary |
| Explore | Transactions, Categories, Merchants, Subscriptions, Transfers, Large Transactions |
| Manage | Overrides, Finance Config |

**Dashboard layout (top to bottom):**
1. Blue gradient banner — "Spending Dashboard"
2. `date_filter()` — preset dropdown + card selector
3. Hero metrics (3 cards) — This Month spend, MoM delta, 3-month average
4. Insights row — category spikes/drops vs 3-month avg
5. Monthly Spend — bar chart with dashed average line (clickable → drilldown)
6. Spending by Category — stacked bar + category cards with trend arrows

### Drilldowns (cross-site pattern)
Clicking a chart bar or table row opens an inline transaction list via `render_drilldown()`.
Implemented on: Dashboard monthly bars, Annual Review monthly bars, Categories chart+table,
Merchants chart+table, Money Summary allocation table.

### Detail pages
All detail pages:
- `sys.path.insert(0, str(Path(__file__).parent.parent))` to import utils
- Call `load_all()` directly (not session_state) so they always show fresh data
- Include a ↺ Reload button that calls `st.cache_data.clear()` + `st.rerun()`
- Filter to `RecordType == "expense"` (except Transactions/Transfers/Money Summary)
- Use custom HTML metric cards (not `st.metric()`) to guarantee color fidelity

### Key pages

**6_Annual_Review.py** — Year + card selector, hero metrics, month-by-month bar with
prior-year overlay, category horizontal bar, fixed vs variable donut, top merchants table,
subscription annual cost table. Monthly bars clickable for drilldown.

**7_Exclusions.py** — Three override actions: Exclude, Override amount, Change category.
Active overrides shown in removable table. Custom Transfer Keywords section: add keywords
that permanently reclassify matching checking rows as RecordType="transfer" in load_all().

**8_Transfers.py** — Date+card filter, hero metrics (Total Transferred, # Transfers,
Avg/Month, Savings Rate if income present), monthly chart, destination breakdown table,
full transfer list.

**9_Money_Summary.py** — Year + card selector, 4 hero metrics (Take-home, Spend, Total
Saved, Savings Rate). Allocation donut (visual) + clickable segment table → inline
drilldown. Contributions breakdown table (prorated from finance_config.csv). View
Transactions radio at bottom (Expenses / Income / Investment Transfers).

**10_Finance_Config.py** — Add/remove manual contribution entries for 401k, HSA, ESPP,
Roth IRA, etc. Used by Money Summary for savings rate calculation.

## Design system
- **Theme:** Light background (#F0F4FA), deep blue accent (#1B3A6B), white cards
- **Fonts:** DM Sans (labels/body), DM Mono (numbers) — loaded from Google Fonts
- **CSS:** All injected via `inject_global_css()` in utils.py
- **Metric cards:** Custom HTML with explicit inline colors (never `st.metric()`)
- **Category colors:** `CAT_COLORS` list in utils.py
- **Section titles:** Left 3px blue border accent via `.section-title` class
- **Buttons:** White bg, #1B3A6B text, light border

## Tests
Run with: `python -m pytest tests/ -v`
- `TestGetConfig` — card config lookup (exact, substring, unknown, default)
- `TestLoadChecking` — checking CSV parsing (income, expense, transfer classification)

## Known gotchas
- **Plotly pie/donut `on_select`** — does NOT fire on click (only box/lasso, which pie
  charts don't support). Use `st.dataframe(on_select="rerun")` for click-to-drilldown
  on breakdowns instead.
- **`st.selectbox` with `key` ignores `index`** after first render — Streamlit uses
  session_state value. Use `st.radio` or separate the click mechanism from the selector.
- `data/` files are gitignored — overrides, custom keywords, finance config, and all
  CSVs live locally only.

## What's planned next
- Recurring expense tuning — confirm/reject heuristic subscriptions, show true annual cost
- Global transaction search across all pages
- Multi-month category trends (sparklines per category)
- Investment goals tracking
- Better data workflow (in-app CSV management)
