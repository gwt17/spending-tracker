# Spending Tracker — Project Roadmap & Architecture

> Last updated: February 2026
> Maintained by: Claude (Cowork / Claude Code sessions)
> Purpose: Single source of truth for project direction, architecture decisions, and backlog

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Current State](#2-current-state)
3. [Architecture Decision: Leaving Streamlit](#3-architecture-decision-leaving-streamlit)
4. [Target Stack](#4-target-stack)
5. [Target Architecture](#5-target-architecture)
6. [Migration Phases](#6-migration-phases)
7. [API Contract](#7-api-contract)
8. [What Carries Over vs What Gets Rebuilt](#8-what-carries-over-vs-what-gets-rebuilt)
9. [Automation Roadmap (Plaid)](#9-automation-roadmap-plaid)
10. [Cost Breakdown](#10-cost-breakdown)
11. [Active Backlog](#11-active-backlog)
12. [Completed Work](#12-completed-work)
13. [Key Decisions & Pushback Log](#13-key-decisions--pushback-log)

---

## 1. Project Vision

A personal finance dashboard that feels like a real SaaS product — comparable in polish and UX to Chase, Empower, or ESPN. The app tracks credit card and checking account spending, savings, investments, and subscriptions. Long-term it should automatically pull transaction data from financial institutions without manual CSV exports.

**Core principles:**
- Data stays private (local-first by default)
- The UI should feel professional, not like an internal tool
- Backend logic should be clean and testable
- Every major feature addition should be spec'd before being built

---

## 2. Current State

**Stack:** Python + Streamlit (multipage)
**Data flow:** Manual CSV export → `merge.py` → `merged.csv` → Streamlit reads and renders
**Status:** Fully polished and stable. Streamlit work is complete — ready for React migration.

### Pages
| Page | Status |
|---|---|
| Dashboard (overview) | ✅ Live |
| Categories | ✅ Live |
| Merchants | ✅ Live |
| Subscriptions | ✅ Live |
| Large Transactions | ✅ Live |
| Transactions | ✅ Live |
| Annual Review | ✅ Live |
| Transfers | ✅ Live |
| Money Summary | ✅ Live |
| Finance Config | ✅ Live |
| Overrides / Exclusions | ✅ Live |

### Known Streamlit limitations that drove the migration decision
- No real layout control — single column flow with fixed sidebar
- No persistent nav, multi-panel views, or dense information architecture
- Interactivity ceiling — no true hover states, modals, slide-out panels, smooth filtering
- Visual ceiling — always looks like Streamlit regardless of CSS injection
- Filter state doesn't propagate from dashboard to detail pages naturally

---

## 3. Architecture Decision: Leaving Streamlit

**Decision:** Migrate to React (frontend) + FastAPI (backend).
**When:** Phase 1 starts next. No further Streamlit feature work — Streamlit is now stable and frozen.

**Why not other backend languages:**
- Python stays because all existing data logic (`utils.py`, `merge.py`) carries over nearly unchanged
- Node.js or Go are valid long-term options but would require rewriting the data processing layer, which uses pandas — no good equivalent in those languages
- Claude Code could migrate to Node.js or Go later if desired, but there is no performance reason to do so for a single-user personal finance app

**Why React:**
- Full layout control — persistent sidebar nav, multi-panel views, dense information architecture
- Real interactivity — hover states, modals, smooth filtering, no full-page reruns
- Industry standard — transferable skill, large ecosystem, excellent documentation
- The owner wants to learn React using this project as the vehicle

---

## 4. Target Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React + Vite (TypeScript) | Modern, fast build tooling; industry standard. Vite chosen over Next.js intentionally — see note below. |
| Styling | Tailwind CSS | Utility-first, learnable, consistent |
| Charts | Recharts | React-native, well-documented |
| Backend | FastAPI (Python) | Keeps existing data logic; fast, modern Python API framework |
| Data storage | CSV files (local) | No change from current — no database needed until Plaid/hosting |
| Package manager | npm (frontend), pip (backend) | Standard for each ecosystem |

> **Why Vite and not Next.js:** Next.js is a full-stack framework that combines frontend and backend in one project. It's a good choice when starting from scratch in TypeScript. This project uses Vite + FastAPI (separate processes) because all data logic lives in Python (pandas, utils.py, merge.py) — there is no good JavaScript equivalent. Rewriting that layer in TypeScript would be wasted effort. FastAPI handles all data; React handles all UI. This separation is intentional and will remain correct through Phase 4 (Plaid).

---

## 5. Target Architecture

### Project Structure
```
Spending_Tracker/
├── backend/
│   ├── main.py               # FastAPI app entry point + CORS config
│   ├── routers/              # One file per domain/page
│   │   ├── dashboard.py
│   │   ├── categories.py
│   │   ├── merchants.py
│   │   ├── subscriptions.py
│   │   ├── transactions.py
│   │   ├── annual_review.py
│   │   ├── transfers.py
│   │   ├── money_summary.py
│   │   ├── large_transactions.py
│   │   ├── finance_config.py
│   │   └── overrides.py
│   ├── utils.py              # Existing — carries over mostly unchanged
│   ├── merge.py              # Existing — unchanged
│   └── data/                 # CSV files — unchanged
└── frontend/
    └── src/
        ├── components/       # Shared UI components (built first)
        │   ├── StatCard.tsx
        │   ├── SectionTitle.tsx
        │   ├── DrilldownTable.tsx
        │   ├── FilterBar.tsx
        │   ├── PageLayout.tsx
        │   └── Chart/
        ├── pages/            # One component per page
        │   ├── Dashboard.tsx
        │   ├── Categories.tsx
        │   └── ...
        ├── hooks/            # Custom React hooks
        │   ├── useDashboard.ts
        │   ├── useTransactions.ts
        │   └── ...
        └── lib/
            └── api.ts        # Centralized API client
```

### Design Principles
- **Backend does all data processing.** React only renders what it receives — no business logic in the frontend.
- **Filter state lives in React.** Date range + card selection are stored in React state and passed as query params to every API call. This solves the filter propagation problem that exists in Streamlit.
- **Component library first.** Before building any page, establish the shared component set. This is what creates the consistent, professional feel.
- **One API endpoint per page.** Clean separation; each page knows exactly what it needs.

---

## 6. Migration Phases

### Phase 1 — Foundation (1–2 Claude Code sessions)
**Goal:** Prove the full stack works end-to-end before committing to the rest.

- Set up FastAPI project structure with CORS
- Set up React + Vite project
- Build shared component library: `StatCard`, `SectionTitle`, `DrilldownTable`, `FilterBar`, `PageLayout`
- Build the Dashboard page end-to-end (hero metrics, monthly chart, insights, category list)
- Verify filter state propagates correctly in React

**Definition of done:** Dashboard loads, shows real data, filters work, drilldowns work.

---

### Phase 2 — Migrate All Pages (1 session per page, roughly)
**Goal:** Full feature parity with Streamlit version.

Order of priority:
1. Categories
2. Merchants
3. Transactions
4. Annual Review
5. Transfers
6. Money Summary
7. Subscriptions
8. Large Transactions
9. Overrides / Exclusions
10. Finance Config

**Learning approach:** After each page is built, review the code together (owner + Claude in Cowork) to understand what React concepts were used and why. Learning React through working code on a project you care about is faster than tutorials.

---

### Phase 3 — Polish ✅ Complete
**Goal:** Achieve the SaaS feel — comparable to Chase, Empower, ESPN.

- ✅ Smooth page transitions (fade-in on every navigation)
- ✅ Loading skeleton states (shimmer effect — no blank flashes while data loads)
- ✅ Empty states with helpful guidance (`EmptyState` component with contextual sub-text)
- ✅ Error states with retry button on all 11 pages
- ✅ Toast notifications for all CRUD actions (Overrides, FinanceConfig)
- ✅ Sidebar Reload Data button with spinning icon + relative timestamp

---

### Phase 4 — Plaid Automation (separate project phase)
**Goal:** Eliminate manual CSV exports. App pulls transactions automatically.

See [Section 9](#9-automation-roadmap-plaid) for full details.

**Prerequisites before starting Phase 4:**
- Phase 3 complete and stable
- Decision made to host the app (Plaid automation requires a running server)
- Authentication added (financial data requires login)

---

## 7. API Contract

All endpoints accept optional query params: `?start=YYYY-MM-DD&end=YYYY-MM-DD&card=CardName`

```
GET  /api/meta                  → available cards, min/max date range
GET  /api/dashboard             → hero metrics, monthly chart data, insights, top categories
GET  /api/categories            → category breakdown with % of spend, avg per txn
GET  /api/merchants             → top merchants by spend, visit count, avg per visit
GET  /api/subscriptions         → detected recurring charges with cadence + cost estimate
GET  /api/transactions          → full transaction list (filterable by RecordType)
GET  /api/annual-review         → year-over-year monthly data, category breakdown, top merchants
GET  /api/transfers             → transfer activity, monthly chart, destination breakdown
GET  /api/money-summary         → income, spend, savings rate, allocation breakdown
GET  /api/large-transactions    → transactions above percentile threshold
GET  /api/finance-config        → manual contribution entries
POST /api/finance-config        → add new contribution entry
DELETE /api/finance-config/:id  → remove entry
GET  /api/overrides             → active override rules
POST /api/overrides             → add override (exclude / amount / recategorize)
DELETE /api/overrides/:id       → remove override
GET  /api/custom-keywords       → custom transfer keywords
POST /api/custom-keywords       → add keyword
DELETE /api/custom-keywords/:id → remove keyword
POST /api/reload                → clear data cache, force re-read from disk
```

---

## 8. What Carries Over vs What Gets Rebuilt

### Carries over (nearly unchanged)
- `utils.py` — all data loading, cleaning, business logic, subscription detection, insights engine
- `merge.py` — CSV merging and deduplication
- `data/` folder structure — CSV files, overrides, finance config, transfer keywords
- All financial logic — proration, savings rate calculation, transfer classification, override application
- Design tokens — accent color `#1B3A6B`, category colors, font choices (DM Sans, DM Mono)

### Gets rebuilt
- All UI files — `app.py` and every `pages/*.py` become FastAPI routers + React components
- CSS — moves from injected Streamlit strings to Tailwind utility classes
- Charts — Plotly → Recharts
- Navigation — Streamlit `st.navigation()` → React Router with persistent sidebar

---

## 9. Automation Roadmap (Plaid)

**What it is:** Plaid is a financial data API used by Empower, Mint, and most fintech apps. It securely connects to banks (including Chase) without storing credentials — users authenticate directly with their bank through Plaid's UI, and Plaid returns an access token the app can use to pull transactions.

**What it would take:**
1. Sign up for Plaid API (free development tier)
2. Build "Connect Account" flow using Plaid Link (their pre-built UI component)
3. Store Plaid access tokens securely on the backend
4. Replace CSV export → `merge.py` workflow with automated Plaid API calls
5. Set up a scheduler for daily transaction pulls
6. Map Plaid's transaction format to the existing data model

**Prerequisites:**
- The app must be hosted (a local-only app can't pull data automatically)
- Authentication is required (this is your financial data — it needs a login)
- A database is needed to store Plaid tokens and transaction history

**Cost:**
- Plaid development mode: free, supports real accounts for personal use
- Plaid production (if sharing with others): ~$0.30–0.50 per connected account/month
- For personal use only, development mode is likely sufficient indefinitely

**Sequencing:** This is Phase 4. Build a great local app first, then add hosting + auth + Plaid on top of a stable foundation.

---

## 10. Cost Breakdown

### Local-only (Phases 1–3)
| Item | Cost |
|---|---|
| Hosting | $0 — runs on your laptop |
| Database | $0 — CSV files |
| Plaid | $0 — not needed yet |
| Domain | $0 — not needed yet |
| **Total** | **$0/month** |

### Hosted (Phase 4+)
| Item | Estimated Cost |
|---|---|
| Backend hosting (Railway or Render) | $5–7/month |
| Frontend hosting (Vercel) | Free tier |
| Database (if needed) | $5–7/month or free tier |
| Plaid (personal use) | $0 (development mode) |
| Domain name (optional) | ~$12/year |
| **Total** | **~$10–15/month** |

**Note:** Language choice (Python vs Node.js vs Go) has no meaningful impact on hosting costs at personal-use scale. Optimize for developer experience, not server performance.

---

## 11. Active Backlog

### React migration (Phases 1–3 — complete ✅)
All pages migrated and polished. Phase 4 (Plaid automation) is next when ready.

| Priority | Page | Status |
|---|---|---|
| 1 | Categories | ✅ Done |
| 2 | Merchants | ✅ Done |
| 3 | Transactions | ✅ Done |
| 4 | Annual Review | ✅ Done |
| 5 | Transfers | ✅ Done |
| 6 | Money Summary | ✅ Done |
| 7 | Subscriptions | ✅ Done |
| 8 | Large Transactions | ✅ Done |
| 9 | Overrides / Exclusions | ✅ Done |
| 10 | Finance Config | ✅ Done |

### Streamlit (correctness fixes only — no new features)
| Priority | Item | Notes |
|---|---|---|
| 1 | None currently | All polish items complete. Only fix bugs if they surface. |

---

## 12. Completed Work

### Session 5 (February 2026) — Phase 3 Polish (complete)
- ✅ `Skeleton.tsx`: StatCardSkeleton, ChartSkeleton, TableSkeleton — shimmer gradient animation
- ✅ `EmptyState.tsx`: centered icon + message + sub-text component
- ✅ `Toast.tsx` + `useToast.ts`: fixed bottom-right toast, auto-dismisses after 3s, green/red for ok/err
- ✅ `PageLayout.tsx`: fade-in animation on every page navigation
- ✅ App.tsx sidebar: Reload Data button with spinning icon + relative timestamp
- ✅ All 11 pages: shimmer skeleton loading states, styled error cards with retry button
- ✅ Overrides + FinanceConfig: all save/delete actions now use toasts

### Session 4 (February 2026) — React + FastAPI Phase 2 (complete)
- ✅ Annual Review page: year + card selectors, grouped bar chart with prior-year ghost bars, category bar chart, fixed/variable donut, top merchants table, subscriptions annual cost table
- ✅ Transfers page: stat cards, sky-blue monthly bar chart, destinations breakdown table, full transfers table
- ✅ Money Summary page: year + card selectors, income-aware hero stats (4 or 3 cards), allocation donut + table, contributions table, tab-switcher for expenses/income/transfers
- ✅ Subscriptions page: FilterBar defaulting to "All time" (new `initialPreset` prop), stat cards, subscription table with cadence badges + total row
- ✅ Large Transactions page: threshold slider with frontend-side filtering (no re-fetch on drag), stat cards, scatter chart by category, transaction table
- ✅ Overrides page: active overrides table with delete, search + action panel (exclude/override/recategorize), custom keyword management
- ✅ Finance Config page: contributions table with delete, add contribution form, info box
- ✅ Backend routers: annual_review.py, transfers.py, money_summary.py, subscriptions.py, large_transactions.py, overrides.py, finance_config.py
- ✅ FilterBar updated with `initialPreset` prop (backwards-compatible)
- ✅ All pages wired into App.tsx and main.py — Phase 2 complete, full feature parity with Streamlit

### Session 3 (February 2026) — React + FastAPI Phase 2 (partial)
- ✅ Categories page: stat cards, horizontal bar chart with per-category colors, breakdown table, drilldown, "Other" grouping threshold slider
- ✅ Merchants page: stat cards, search with debounce, top-N slider, horizontal bar chart, detail table, drilldown
- ✅ Transactions page: full filter row (search, category, record type, sort), amount range inputs, summary bar, transaction table with category badges, green income rows, transfer keywords disclosure
- ✅ Backend routers: categories.py, merchants.py, transactions.py
- ✅ All three pages wired into App.tsx sidebar navigation

### Session 2 (February 2026) — React + FastAPI Phase 1
- ✅ New project created at `Finance/finance-dashboard/` (separate from Streamlit app)
- ✅ FastAPI backend with CORS, in-memory cache, POST /api/reload
- ✅ `utils.py` ported — all Streamlit code stripped, pure data logic preserved
- ✅ API endpoints: GET /api/meta, GET /api/dashboard, GET /api/dashboard/drilldown
- ✅ React + Vite + TypeScript + Tailwind CSS v4 + Recharts + React Router
- ✅ Shared component library: StatCard, SectionTitle, FilterBar, PageLayout, DrilldownTable
- ✅ Dashboard page: banner, filter bar, hero metrics, insights row, monthly bar chart, category list, drilldown
- ✅ Sidebar navigation with all sections (Overview, Review, Explore, Manage) — stub pages for all routes
- ✅ `launch.command` and `stop.command` scripts (double-clickable on Mac)
- ✅ App verified end-to-end: real data loads, filters work, chart clickthrough works

### Session 1 (February 2026) — Streamlit audit + refactor
- ✅ Comprehensive codebase audit (bugs, tech debt, UX issues, roadmap gaps)
- ✅ Large Transactions page restored to sidebar navigation (was orphaned)
- ✅ `_stat()` HTML card helper centralized — removed 6 duplicate copies, added `render_stat_card()` to `utils.py`
- ✅ Nav bar (← Dashboard / ↺ Reload) centralized — removed 7 duplicate blocks, added `render_nav_bar()` to `utils.py`
- ✅ Money Summary proration bug fixed — empty year now returns `0.0` instead of `1.0`
- ✅ Silent override failure fixed — `check_data_warnings()` added, surfaces warning if `overrides.csv` is malformed
- ✅ Date labels standardized — charts now show "Nov 2025" instead of "2025-11"; `format_year_month()` added to `utils.py`
- ✅ Custom transfer keyword normalization — confirmed already handled correctly (no change needed)

### Session 1 continued (February 2026) — Streamlit UX polish
- ✅ Filters moved above hero metrics on Dashboard — removed `hero_slot` placeholder pattern, now renders in natural top-to-bottom order
- ✅ Insights capped at 4, overflow hidden — `insights[:4]` in `compute_insights()`, `.insight-row { overflow: hidden }`
- ✅ $0 insights suppressed — `if this_month == 0: continue` guard added in `compute_insights()`
- ✅ Section spacing improved — `.section-title` margin updated to `36px 0 14px 0`; spacers added after insights row and monthly chart
- ✅ `card-primary` CSS class added for primary metric card accent style
- ✅ Background lightened from `#F0F4FA` to `#F8FAFC` for cleaner look
- ✅ Subscriptions table — Est Annual column added
- ✅ Architecture and migration plan documented in this ROADMAP

---

## 13. Key Decisions & Pushback Log

This section captures architectural decisions, tradeoffs considered, and cases where the recommended direction differed from initial instinct.

---

**Decision: Migrate from Streamlit to React + FastAPI**
*Rationale:* Streamlit has a hard ceiling on layout control, interactivity, and visual polish. The target aesthetic (Chase, Empower, ESPN) is not achievable in Streamlit regardless of CSS effort. The migration cost is justified because Python data logic carries over intact.

---

**Decision: Keep Python as the backend language**
*Considered:* Node.js (same language as frontend), Go (performance)
*Rejected because:* Owner knows Python; existing data logic uses pandas which has no good equivalent in Node.js or Go; performance difference is irrelevant at single-user scale. Claude Code could migrate later if desired.
*Pushback noted:* Do not switch languages to save on hosting costs — the difference at this scale is negligible.

---

**Decision: Local-first, no database until Phase 4**
*Rationale:* A database adds complexity without adding value until Plaid automation is needed. CSV files work fine for local personal use.

---

**Decision: Build component library before pages**
*Rationale:* The consistent, professional feel of apps like Chase comes from a design system, not individual page effort. Building shared components first ensures every page inherits the same visual language from day one.

---

**Decision: Skip filter propagation as a Streamlit fix**
*Rationale:* This is a structural limitation of Streamlit that React solves naturally. Investing engineering time in a Streamlit workaround is wasted effort given the impending migration.

---

**Decision: No more Streamlit feature work**
*Rationale:* Every hour spent improving Streamlit UI is work that doesn't transfer to the React version. Streamlit is now stable and frozen — correctness fixes only going forward.

---

**Decision: Learn React through the project, not tutorials**
*Approach:* Claude Code writes the code; owner reviews it with Claude (Cowork) after each page is built to understand the React concepts used. Learning through real, working code on a project you care about is faster than abstract tutorials.

---

**Plaid integration: Phase 4, not earlier**
*Rationale:* Requires a hosted app, authentication, and a database — none of which exist yet. Adding it before the foundation is stable means doing it twice. Build the great local app first.
