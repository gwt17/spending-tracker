# Spending Tracker — Learning Log

> Maintained by: Claude (Cowork sessions)
> Purpose: Track concepts introduced each session so you can deepen your understanding over time.
> Format: Each session gets an entry. Read the entry *after* the Claude Code session for that phase to see the concepts in working code.

---

## How to use this file

After each Claude Code session, come back here and read the entry for that phase. The goal isn't to memorize anything — it's to recognize the patterns when you see them in the code. Over time they'll become second nature.

If you want to go deeper on any concept, the resources at the bottom of each entry point you in the right direction.

---

## Session 1 (February 2026) — Codebase audit + Streamlit polish

### What we did
Audited the full Streamlit codebase, fixed real bugs, and polished the UI. Also made the decision to migrate to React + FastAPI and documented the full architecture in ROADMAP.md.

### Concepts introduced

**Refactoring: DRY (Don't Repeat Yourself)**
We found the same HTML card helper (`_stat()`) copy-pasted into 6 different files, and the same nav bar block copy-pasted into 7 files. We extracted both into shared functions in `utils.py` (`render_stat_card()` and `render_nav_bar()`). Now there's one source of truth — change it once, it updates everywhere.

This is the single most important software principle. If you find yourself copying and pasting code, that's the signal to extract a shared function.

**Proration**
Money Summary calculates your savings rate for a selected year. If you only have data for part of a year (say, 8 out of 12 months), your 401k contribution shouldn't count as a full year's worth. Proration scales the annual number down to match how much of the year is covered by your data.

Bug we fixed: the proration function returned `1.0` (100%) for years with no data at all, making contributions appear at full value. Fixed to return `0.0`.

**Cache invalidation**
Streamlit's `@st.cache_data` stores the result of `load_all()` in memory so it doesn't re-read CSVs on every page load. The tradeoff: if you add new overrides or reload CSVs, the cached (stale) data is still shown. The ↺ Reload button fixes this by calling `st.cache_data.clear()` then `st.rerun()`. This pattern shows up in almost every caching system.

**Defensive programming**
We added `check_data_warnings()` which reads `overrides.csv` and checks for malformed rows before they silently cause wrong results. The principle: fail loudly and early, with a clear message. Silent failures are the hardest bugs to diagnose.

---

## Session 2 (February 2026) — React + FastAPI Phases 1 & 2

### What we built
Phases 1 and 2 are complete. The full React + FastAPI app is running:
- FastAPI backend with all routers (dashboard, categories, merchants, transactions, and more)
- React frontend with persistent sidebar navigation, shared component library, and real pages for Dashboard, Categories, Merchants, and Transactions
- `launch.command` and `stop.command` for double-click startup/shutdown

### The big picture: two servers, one app

When you double-click `launch.command`, two programs start on your computer at the same time:

- **FastAPI** (Python) — runs at `localhost:8000`. Reads your CSV files and answers data questions.
- **React** (JavaScript) — runs at `localhost:5173`. This is what you see in the browser.

When you click a page, React sends a question to FastAPI ("give me the categories data for the last 12 months"). FastAPI crunches the numbers and sends back the answer. React draws the page. Neither side does the other's job — Python handles all data, React handles all visuals.

The old Streamlit app was one program doing both. This is cleaner, faster, and why the app now looks and feels more professional.

### What is an API?

API stands for "Application Programming Interface" — an unhelpful name. Here's what it actually is: a list of questions you're allowed to ask a server, and what you'll get back.

Your FastAPI backend publishes a list of these questions called **endpoints**. Look at `backend/main.py`:

```python
app.include_router(dashboard.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(merchants.router, prefix="/api")
```

Each line adds a set of endpoints to the list. The `prefix="/api"` means every URL starts with `/api/`. So you end up with: `GET /api/dashboard`, `GET /api/categories`, `GET /api/merchants`, etc.

**GET** means "I want to get data." Inside `backend/routers/dashboard.py`:

```python
@router.get("/dashboard")
def get_dashboard(start=None, end=None, card="All cards", preset="Last 12 months"):
    df = load_all()
    # ... filter, compute ...
    return { "hero": {...}, "monthly_chart": [...], ... }
```

The `@router.get("/dashboard")` says: *when someone asks GET /api/dashboard, run this function.* The function reads your CSVs, does the math, and returns a Python dictionary. FastAPI converts that dictionary to **JSON** (a simple text format) and sends it back.

You can see this live: while the app is running, open `http://localhost:8000/api/dashboard` in a browser tab. That raw JSON is exactly what React receives. You can also visit `http://localhost:8000/docs` to see an interactive page listing every endpoint — try them by hand.

### npm and package.json

npm is to JavaScript what pip is to Python — it installs libraries. `frontend/package.json` is the equivalent of `requirements.txt`:

```json
"dependencies": {
    "react": "^19.0.0",
    "react-router-dom": "^7.1.1",
    "recharts": "^2.15.0"
},
"devDependencies": {
    "vite": "^6.0.5",
    "typescript": "~5.7.2",
    "tailwindcss": "^4.0.0"
}
```

`dependencies` are libraries the app uses at runtime. `devDependencies` are tools only needed during development (Vite, TypeScript, Tailwind). The `scripts` section defines shortcuts:

```json
"scripts": {
    "dev": "vite"
}
```

When you run `npm run dev`, it runs Vite, which starts the development server. `npm install` reads the file and installs everything into `node_modules` (same concept as `.venv`).

### React: components

Everything you see is a **component** — a function that returns HTML-like code. Your `StatCard` is a clean example (`frontend/src/components/StatCard.tsx`):

```tsx
const StatCard = ({ label, value, sub, valueColor, primary = false }) => {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm ...">
      <div className="text-[11px] uppercase ...">{label}</div>
      <div style={{ color: valueColor }}>{value}</div>
      {sub && <div>{sub}</div>}
    </div>
  );
};
```

`label`, `value`, `sub`, `valueColor`, `primary` are **props** — the inputs, like function arguments. The HTML-looking code inside is **JSX** — JavaScript that looks like HTML. Curly braces `{}` drop a value into the markup: `{label}` puts the label text there. `{sub && <div>{sub}</div>}` means "only show this if sub has a value."

In `Dashboard.tsx` it's used like:

```tsx
<StatCard label="This Month" value={fmt(data.hero.this_month)} primary />
```

Exactly like calling a function with named arguments, just in JSX syntax. `primary` alone (no `=`) is shorthand for `primary={true}`.

### State: how the app remembers things

**State** is data a component tracks. When state changes, React automatically re-renders that component. Look at `FilterBar.tsx`:

```tsx
const [preset, setPreset] = useState("Last 12 months");
const [card, setCard] = useState("All cards");
```

`useState` gives you the current value and a function to update it. When the user changes the dropdown:

```tsx
onChange={(e) => setPreset(e.target.value)}
```

`setPreset` is called → state changes → React re-renders the component → dropdown shows the new value. Automatic.

`Dashboard.tsx` owns the filter state and passes `setFilters` down to `FilterBar`:

```tsx
const [filters, setFilters] = useState({ preset: "Last 12 months", card: "All cards", ... });
<FilterBar onFilterChange={setFilters} />
```

When you change a filter, `FilterBar` calls `onFilterChange` (which is `setFilters`), which updates state in Dashboard, which triggers a data re-fetch. The whole page updates. This is the clean filter propagation that Streamlit couldn't do.

### Hooks: useEffect and custom hooks

A **hook** is a special function that gives a component a capability. They always start with `use`.

`useEffect` runs code when something changes. In `hooks/useDashboard.ts`:

```tsx
useEffect(() => {
  setLoading(true);
  fetch(`/api/dashboard?preset=${filters.preset}&card=${filters.card}`)
    .then(r => r.json())
    .then(json => {
      setData(json);
      setLoading(false);
    });
}, [filters.preset, filters.start, filters.end, filters.card]);
```

The array at the end is the **dependency list** — re-run this whenever any of those values changes. So every time you change the date preset or card, this fires automatically, fetches fresh data, and updates the page.

`useDashboard` is a **custom hook** that wraps all this fetch logic. Instead of 30 lines inside the component, `Dashboard.tsx` just calls:

```tsx
const { data, loading, error } = useDashboard(filters);
```

One line. It gets back the data, a loading boolean, and an error message if something went wrong. Clean and reusable.

### TypeScript: what the extra syntax means

TypeScript is JavaScript with types. The `interface` keyword describes what shape an object must have:

```tsx
interface StatCardProps {
  label: string;    // must be text
  value: string;
  sub?: string;     // ? means optional
}
```

If you accidentally pass a number where a string is expected, TypeScript underlines it red before you even run the code. It catches mistakes early. At runtime it behaves identically to regular JavaScript — TypeScript is purely a development-time tool.

The `.tsx` extension means TypeScript + JSX. The `.ts` extension (hooks, API files) means TypeScript without JSX.

### How it all connects: one complete flow

What happens when you change the filter to "Last 3 months":

1. Dropdown `onChange` fires → `setPreset("Last 3 months")` in FilterBar
2. FilterBar calls `onFilterChange` → `filters` state in Dashboard updates
3. `filters` changed → `useEffect` in `useDashboard` fires → `setLoading(true)`
4. `fetch("/api/dashboard?preset=Last+3+months&card=All+cards")` — HTTP request leaves the browser
5. FastAPI receives it → runs `get_dashboard()` in `routers/dashboard.py`
6. Python reads `merged.csv`, filters to last 3 months, calculates hero metrics, builds chart data
7. Returns Python dict → FastAPI converts to JSON → sends HTTP response back
8. `fetch` resolves → `setData(json)` → `setLoading(false)`
9. `data` state updated → Dashboard re-renders → numbers and chart update

Under 100ms. No page reload, no flicker — just the numbers change.

### Resources to go deeper
- **React official docs** — react.dev/learn — Interactive tutorial covering components, props, and state. About 2 hours.
- **Tailwind CSS docs** — tailwindcss.com/docs — Searchable reference for every utility class. Keep this open while working.
- **FastAPI docs** — fastapi.tiangolo.com — Best API docs of any framework. The tutorial section is fast and clear.
- **Recharts docs** — recharts.org/examples — Example-first. Find your chart type, copy the example, adapt it.
- **TypeScript handbook** — typescriptlang.org/docs/handbook/intro.html — Start with "The Basics." Skip anything about classes.

---

## Session 3 (February 2026) — Phase 3 Polish

### What was built
Loading skeletons, page transitions, empty states, error states, and toast notifications across all 11 pages. The app now feels like a real SaaS product — no blank flashes, no silent failures, feedback on every action.

### The principle behind all of it

A professional app communicates its state at every moment. There are four states every page needs to handle:

| State | Before Phase 3 | After Phase 3 |
|---|---|---|
| Loading | "Loading..." text | Shimmer skeleton matching real layout |
| Error | Raw error text | Styled card with icon + retry button |
| Empty | Blank space | EmptyState with explanation |
| Success | ✅ Already good | ✅ Already good |

This is what separates something that feels like Chase from something that feels like an internal tool.

### CSS animations: `@keyframes`

Three animations were added to `index.css`:

```css
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}
@keyframes fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
```

`@keyframes` defines a named animation — you describe start and end, the browser fills in everything between. The three cover the main motion needs: shimmer (loading), fadein (page transitions), spin (reload icon).

### Skeleton loading states

Skeleton loaders show the **shape of the content** before data arrives. The user's eye parses the layout while loading — when real content drops in, it feels smooth. Three variants: `StatCardSkeleton`, `ChartSkeleton({ height })`, `TableSkeleton({ rows })`. Each page uses whichever combination matches its real layout.

### New hooks: `useRef` and `useCallback`

**`useRef`** stores a value that persists across renders *without* triggering a re-render when it changes. The toast hook uses it to hold the auto-dismiss timer ID so it can be cancelled if a second toast fires quickly. If `useState` were used instead, updating the timer ID would cause an extra re-render.

**`useCallback`** memoizes a function — returns the same function reference across renders unless its dependencies change. Used on `showToast` so it can be passed to children without causing unnecessary re-renders.

| Hook | Triggers re-render | Use for |
|---|---|---|
| `useState` | ✅ Yes | Things you display on screen |
| `useRef` | ❌ No | Timers, DOM refs, values you track but don't display |
| `useCallback` | N/A | Functions you pass down to children |

### The `key` trick for re-triggering animations

In `Toast.tsx`, the element has `key={toast.id}` where `id` is `Date.now()`. Giving an element a new `key` forces React to unmount and remount it from scratch, re-triggering the `fadein` animation even when two toasts have the same message. Without this, React reuses the existing element and the animation doesn't replay.

---

## Running glossary

Terms that come up repeatedly across sessions.

| Term | What it means |
|---|---|
| Component | A React function that returns JSX (HTML-like syntax). Building block of all React UIs. |
| Props | Data passed into a component, like function arguments. |
| State | Data a component tracks internally. Changing state triggers a re-render. |
| Hook | A special React function (starts with `use`) that adds capabilities to a component — `useState`, `useEffect`, etc. |
| JSX | HTML-like syntax used inside React components. It compiles to JavaScript. |
| Tailwind | CSS utility class library. You style things by adding classes like `text-sm font-bold text-blue-700`. |
| Recharts | React charting library. Charts are components that accept data as props. |
| FastAPI | Python web framework for building JSON APIs. Replaces Streamlit as the data layer. |
| CORS | Browser security mechanism. Configured in FastAPI to allow the React frontend to call the backend. |
| Endpoint | A URL on the backend that returns data. E.g., `/api/dashboard`. |
| JSON | The format data travels between backend and frontend. Python dicts/lists serialize to JSON automatically in FastAPI. |
| `useEffect` | React hook for running code when a component loads or when a value changes (e.g., fetch data on mount). |
| `useState` | React hook for storing and updating component state. |
| `useRef` | React hook that stores a value across renders without triggering a re-render. Used for timers, DOM refs. |
| `useCallback` | React hook that memoizes a function — returns the same reference across renders. Prevents unnecessary re-renders. |
| Vite | The build tool for the React project. Handles fast development reloads and production bundling. |
| Router | React Router — lets you define multiple pages in a React app without full page reloads. |
| DRY | "Don't Repeat Yourself" — the principle that drives extracting shared functions and components. |
| Proration | Scaling an annual number down to match a partial year of data coverage. |
| Cache | Stored result of an expensive operation. Needs to be cleared when the underlying data changes. |
| RecordType | Column in the merged dataset. Values: `expense`, `income`, `transfer`. Controls which rows appear on which pages. |
| Skeleton loader | A shimmering placeholder matching the shape of content while data loads. Better UX than a spinner or blank space. |
| `@keyframes` | CSS syntax to define a named animation. You describe start and end states; the browser interpolates. |
| Toast | A small temporary notification (bottom-right) that auto-dismisses. Used for save/delete confirmations. |
| Empty state | A designed placeholder when a list has no content. Explains why and suggests an action. |
