import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from utils import (
    CUSTOM_KEYWORDS_PATH,
    OVERRIDES_PATH,
    TRANSFER_KEYWORDS,
    inject_global_css,
    load_all,
    load_custom_keywords,
    load_overrides,
    save_custom_keyword,
    save_override,
)

inject_global_css()

# ── Nav bar ───────────────────────────────────────────────────────────────────
nav_l, nav_r = st.columns([6, 1])
with nav_l:
    st.markdown(
        "<a href='/' target='_self' style='font-family:\"DM Sans\",sans-serif;font-size:13px;"
        "color:#1B3A6B;text-decoration:none;font-weight:500;'>← Dashboard</a>",
        unsafe_allow_html=True,
    )
with nav_r:
    if st.button("↺ Reload", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1B3A6B 0%, #2563EB 100%);
    border-radius: 10px;
    padding: 14px 24px;
    margin-bottom: 16px;
">
    <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:white;letter-spacing:-0.02em;">
        Transaction Overrides
    </div>
</div>
""", unsafe_allow_html=True)

# ── Active Overrides ──────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Active Overrides</div>", unsafe_allow_html=True)

ov = load_overrides()

if ov.empty:
    st.markdown(
        "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#94A3B8;"
        "padding:10px 0 16px;'>No overrides yet. Use the section below to get started.</div>",
        unsafe_allow_html=True,
    )
else:
    def _effect(r):
        if r["Action"] == "exclude":
            return "Excluded"
        if r["Action"] == "override":
            try:
                return f"Amount → ${float(r['NewAmount']):,.2f}"
            except (ValueError, TypeError):
                return "Override"
        if r["Action"] == "recategorize":
            return f"Category → {r.get('NewCategory', '')}"
        return r["Action"]

    ov_display = ov.copy()
    ov_display["Effect"] = ov_display.apply(_effect, axis=1)
    ov_display = ov_display.rename(columns={"OriginalAmount": "Original Amount"})

    show_cols = ["Date", "Description", "Original Amount", "Effect"]
    col_config = {
        "Original Amount": st.column_config.NumberColumn("Original Amount", format="$%.2f"),
    }
    # Only show Notes column if at least one note has content
    has_notes = (
        "Notes" in ov_display.columns
        and ov_display["Notes"].astype(str).str.strip().ne("").any()
    )
    if has_notes:
        show_cols.append("Notes")

    event_ov = st.dataframe(
        ov_display[show_cols],
        on_select="rerun",
        selection_mode="multi-row",
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
    )

    sel_ov = event_ov.selection["rows"]
    if sel_ov:
        label = f"Remove {len(sel_ov)} selected override{'s' if len(sel_ov) > 1 else ''}"
        if st.button(label, type="primary"):
            updated = ov.drop(index=sel_ov).reset_index(drop=True)
            updated.to_csv(OVERRIDES_PATH, index=False)
            st.cache_data.clear()
            st.rerun()

# ── Find & Override ───────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Find & Override</div>", unsafe_allow_html=True)

df_all = load_all()
if df_all.empty:
    st.error("No data found. Drop CSVs into `data/` and click Reload.")
    st.stop()

df_exp = df_all[df_all["RecordType"] == "expense"].copy()
all_categories = sorted(df_all["Category"].dropna().unique().tolist())

search_col, year_col = st.columns([3, 1])
with search_col:
    search = st.text_input(
        "Search",
        placeholder="Search by description — e.g. Withdrawal, Amazon, Target…",
        label_visibility="collapsed",
    )
with year_col:
    years = ["All years"] + sorted(df_exp["Date"].dt.year.unique().tolist(), reverse=True)
    year_filter = st.selectbox("Year", years, label_visibility="collapsed")

if search:
    df_exp = df_exp[df_exp["Description"].str.contains(search, case=False, na=False)]
if year_filter != "All years":
    df_exp = df_exp[df_exp["Date"].dt.year == int(year_filter)]

df_sorted = df_exp.sort_values(["Date", "Amount"], ascending=[False, False]).head(300)

if df_sorted.empty:
    st.info("No transactions match. Try a different search term or year.")
else:
    df_display = df_sorted[["Date", "Description", "Amount", "Category", "Card"]].copy()
    df_display["Date"]   = df_display["Date"].dt.strftime("%Y-%m-%d")
    df_display["Amount"] = df_display["Amount"].round(2)
    df_display = df_display.reset_index(drop=True)

    st.markdown(
        "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;"
        "margin-bottom:6px;'>Click a row to select it, then choose an action below.</div>",
        unsafe_allow_html=True,
    )

    event_txn = st.dataframe(
        df_display,
        on_select="rerun",
        selection_mode="single-row",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
        },
    )

    sel_rows = event_txn.selection["rows"]
    if sel_rows:
        row = df_display.iloc[sel_rows[0]]

        st.markdown(
            f"<div style='background:white;border-radius:10px;padding:14px 20px;"
            f"box-shadow:0 2px 8px rgba(27,58,107,0.08);border:1px solid rgba(27,58,107,0.07);"
            f"margin:12px 0;font-family:\"DM Sans\",sans-serif;font-size:14px;color:#0F172A;'>"
            f"Selected: <strong>{row['Description']}</strong> &nbsp;·&nbsp; "
            f"<strong style='font-family:\"DM Mono\",monospace;'>${float(row['Amount']):,.2f}</strong>"
            f" &nbsp;·&nbsp; {row['Date']} &nbsp;·&nbsp; "
            f"<span style='color:#64748B;'>{row['Category']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Action panel ──────────────────────────────────────────────────────
        action_col, detail_col = st.columns([2, 3])
        with action_col:
            action = st.radio(
                "Action",
                ["Exclude", "Override amount", "Change category"],
                horizontal=False,
                key="override_action",
            )

        new_amount   = None
        new_category = None

        with detail_col:
            if action == "Override amount":
                new_amount = st.number_input(
                    "New amount ($)",
                    min_value=0.0,
                    value=float(row["Amount"]),
                    step=1.0,
                    format="%.2f",
                    key="override_new_amount",
                )
            elif action == "Change category":
                current_idx = all_categories.index(row["Category"]) if row["Category"] in all_categories else 0
                new_category = st.selectbox(
                    "New category",
                    all_categories,
                    index=current_idx,
                    key="override_new_cat",
                )

        notes = st.text_input(
            "Note (optional) — e.g. 'reimbursed by team', 'one-time anomaly'",
            key="override_notes",
            placeholder="Add a note so you remember why this was changed…",
        )

        if st.button("Save Override", type="primary"):
            action_key = (
                "exclude"       if action == "Exclude"          else
                "override"      if action == "Override amount"  else
                "recategorize"
            )
            save_override(
                date_str=row["Date"],
                description=row["Description"],
                original_amount=float(row["Amount"]),
                action=action_key,
                new_amount=new_amount,
                new_category=new_category,
                notes=notes.strip() if notes else None,
            )
            st.cache_data.clear()
            st.success(f"Override saved for '{row['Description']}'. Data refreshed.")
            st.rerun()

# ── Custom Transfer Keywords ──────────────────────────────────────────────────
st.markdown("<div class='section-title'>Custom Transfer Keywords</div>", unsafe_allow_html=True)
st.markdown(
    "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#475569;"
    "margin-bottom:16px;line-height:1.6;'>"
    "Checking account transactions whose description contains any of these keywords "
    "are excluded as transfers — they won't count as income or expenses. "
    "Useful for cash withdrawals, ACH transfers to accounts not already in the built-in list, etc."
    "</div>",
    unsafe_allow_html=True,
)

# Built-in keywords (read-only)
with st.expander("Built-in keywords (always active)", expanded=False):
    builtin_html = " &nbsp;·&nbsp; ".join(
        f"<code style='font-family:\"DM Mono\",monospace;font-size:12px;"
        f"background:#F1F5F9;padding:2px 6px;border-radius:4px;color:#1B3A6B;'>{kw}</code>"
        for kw in sorted(TRANSFER_KEYWORDS)
    )
    st.markdown(
        f"<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;"
        f"color:#475569;padding:4px 0;line-height:2;'>{builtin_html}</div>",
        unsafe_allow_html=True,
    )

# Custom keywords
kws = load_custom_keywords()

if kws.empty:
    st.markdown(
        "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#94A3B8;"
        "padding:4px 0 12px;'>No custom keywords yet.</div>",
        unsafe_allow_html=True,
    )
else:
    event_kw = st.dataframe(
        kws,
        on_select="rerun",
        selection_mode="multi-row",
        use_container_width=True,
        hide_index=True,
        key="kw_table",
    )
    sel_kw = event_kw.selection["rows"]
    if sel_kw:
        label = f"Remove {len(sel_kw)} selected keyword{'s' if len(sel_kw) > 1 else ''}"
        if st.button(label, type="primary", key="remove_kw_btn"):
            updated_kws = kws.drop(index=sel_kw).reset_index(drop=True)
            updated_kws.to_csv(CUSTOM_KEYWORDS_PATH, index=False)
            st.cache_data.clear()
            st.rerun()

# Add new keyword form
st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
kw_input_col, kw_note_col, kw_btn_col = st.columns([2, 3, 1.2])
with kw_input_col:
    new_kw = st.text_input(
        "Keyword",
        placeholder="e.g. withdrawal, paypal, zelle…",
        label_visibility="collapsed",
        key="new_kw_input",
    )
with kw_note_col:
    new_kw_note = st.text_input(
        "Note",
        placeholder="Note (optional) — e.g. 'ATM cash withdrawals'",
        label_visibility="collapsed",
        key="new_kw_note",
    )
with kw_btn_col:
    if st.button("Add Keyword", use_container_width=True, key="add_kw_btn"):
        if new_kw.strip():
            added = save_custom_keyword(new_kw.strip(), new_kw_note.strip())
            if added:
                st.cache_data.clear()
                st.success(f"'{new_kw.strip()}' added. Data refreshed.")
                st.rerun()
            else:
                st.warning(f"'{new_kw.strip()}' is already in your keyword list.")
