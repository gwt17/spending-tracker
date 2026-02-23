import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from utils import (
    FINANCE_CONFIG_PATH,
    inject_global_css,
    load_finance_config,
    save_finance_config_entry,
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
        Finance Config
    </div>
</div>
""", unsafe_allow_html=True)

# ── Active contributions ───────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Contributions</div>", unsafe_allow_html=True)

cfg = load_finance_config()

if cfg.empty:
    st.markdown(
        "<div style='font-family:\"DM Sans\",sans-serif;font-size:13px;color:#94A3B8;"
        "padding:10px 0 16px;'>No contributions configured yet. Add them below.</div>",
        unsafe_allow_html=True,
    )
else:
    display = cfg.copy()
    display["Annual (You)"]      = display["AmountPerYear"].apply(lambda x: f"${x:,.0f}")
    display["Annual (Employer)"] = display["EmployerMatch"].apply(
        lambda x: f"${x:,.0f}" if float(x) > 0 else "—"
    )
    display["Monthly (Est.)"] = (display["AmountPerYear"] / 12).apply(lambda x: f"${x:,.0f}")

    event_cfg = st.dataframe(
        display[["Name", "Type", "Annual (You)", "Annual (Employer)", "Monthly (Est.)", "Notes"]],
        on_select="rerun",
        selection_mode="multi-row",
        use_container_width=True,
        hide_index=True,
        key="cfg_table",
    )

    sel = event_cfg.selection["rows"]
    if sel:
        label = f"Remove {len(sel)} selected entr{'ies' if len(sel) > 1 else 'y'}"
        if st.button(label, type="primary"):
            updated = cfg.drop(index=sel).reset_index(drop=True)
            updated.to_csv(FINANCE_CONFIG_PATH, index=False)
            st.rerun()

# ── Add contribution ──────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Add Contribution</div>", unsafe_allow_html=True)

CONTRIBUTION_TYPES = [
    "Pre-tax (401k / Traditional IRA / HSA)",
    "After-tax (Roth IRA / ESPP)",
    "Employer Match",
]

with st.form("add_contribution"):
    c1, c2 = st.columns([2, 2])
    with c1:
        name = st.text_input("Name", placeholder="e.g. 401k, HSA, Roth IRA, ESPP")
    with c2:
        type_ = st.selectbox("Type", CONTRIBUTION_TYPES)

    c3, c4 = st.columns([2, 2])
    with c3:
        amount = st.number_input(
            "Your Annual Contribution ($)",
            min_value=0.0, value=0.0, step=100.0, format="%.2f",
        )
    with c4:
        match = st.number_input(
            "Employer Annual Match ($)",
            min_value=0.0, value=0.0, step=100.0, format="%.2f",
            help="Leave at 0 if no employer match or if tracking match separately.",
        )

    notes = st.text_input("Note (optional)", placeholder="e.g. 'maxed out', '5% of salary'")

    submitted = st.form_submit_button("Add Contribution", type="primary")
    if submitted:
        if not name.strip():
            st.error("Name is required.")
        elif amount == 0 and match == 0:
            st.error("Enter an amount for your contribution and/or employer match.")
        else:
            save_finance_config_entry(
                name=name,
                type_=type_,
                amount_per_year=amount,
                employer_match=match,
                notes=notes,
            )
            st.success(f"'{name.strip()}' added.")
            st.rerun()

# ── Info box ──────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='font-family:\"DM Sans\",sans-serif;font-size:12px;color:#94A3B8;"
    "margin-top:16px;line-height:1.7;'>"
    "<strong style='color:#64748B;'>Pre-tax</strong> contributions (401k, HSA) reduce your taxable income — "
    "they're deducted from your paycheck before it hits your checking account, so they won't appear in your CSV exports.<br>"
    "<strong style='color:#64748B;'>After-tax</strong> contributions (Roth IRA, ESPP) come from take-home pay and "
    "may or may not appear as transfers depending on your setup.<br>"
    "Amounts entered here are used to estimate your true savings rate on the Money Summary page."
    "</div>",
    unsafe_allow_html=True,
)
