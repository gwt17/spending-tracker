"""
Tests for utils.py business logic.

Run with:  python -m pytest tests/ -v
"""
import datetime

import pandas as pd
import pytest

# Add parent dir so we can import utils without installing it as a package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    clean_merchant, compute_date_range, compute_insights, detect_subscriptions,
    _get_config, _load_checking, CARD_CONFIG, CC_PAYMENT_KEYWORDS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal transactions DataFrame from a list of dicts."""
    df = pd.DataFrame(rows)
    df["Date"]      = pd.to_datetime(df["Date"])
    df["YearMonth"] = df["Date"].dt.to_period("M")
    return df


# ── clean_merchant ────────────────────────────────────────────────────────────

class TestCleanMerchant:
    def test_strips_hash_location_code(self):
        assert clean_merchant("WHOLEFDS MKT #10432") == "Wholefds Mkt"

    def test_strips_trailing_4digit_number(self):
        assert clean_merchant("STARBUCKS STORE 12345") == "Starbucks Store"

    def test_strips_trailing_state_code(self):
        assert clean_merchant("WHOLEFDS MKT TX") == "Wholefds Mkt"

    def test_title_cases_all_caps(self):
        assert clean_merchant("AMAZON") == "Amazon"

    def test_leaves_mixed_case_alone(self):
        # Already title-cased names should not be changed
        assert clean_merchant("Netflix.com") == "Netflix.com"

    def test_leaves_short_numbers_alone(self):
        # 3-digit numbers should not be stripped (too aggressive)
        result = clean_merchant("ROUTE 66 DINER")
        assert "66" in result

    def test_handles_empty_string(self):
        assert clean_merchant("") == ""

    def test_strips_hash_and_state(self):
        assert clean_merchant("WHOLEFDS MKT #10432 TX") == "Wholefds Mkt"


# ── compute_date_range ────────────────────────────────────────────────────────

class TestComputeDateRange:
    # Reference point: today = Feb 20, 2026
    TODAY    = datetime.date(2026, 2, 20)
    MIN_DATE = datetime.date(2024, 1, 1)
    MAX_DATE = datetime.date(2026, 2, 20)

    def _range(self, choice):
        return compute_date_range(choice, self.TODAY, self.MIN_DATE, self.MAX_DATE)

    def test_last_month_start_is_jan_1(self):
        start, end = self._range("Last month")
        assert start == datetime.date(2026, 1, 1)

    def test_last_month_end_is_jan_31(self):
        """Critical: last month must end on Jan 31, not today."""
        start, end = self._range("Last month")
        assert end == datetime.date(2026, 1, 31)

    def test_last_month_and_ytd_differ(self):
        """The original bug: these were returning the same end date."""
        _, end_last_month = self._range("Last month")
        _, end_ytd        = self._range("YTD")
        assert end_last_month != end_ytd

    def test_ytd_starts_jan_1_current_year(self):
        start, _ = self._range("YTD")
        assert start == datetime.date(2026, 1, 1)

    def test_ytd_ends_today(self):
        _, end = self._range("YTD")
        assert end == self.TODAY

    def test_last_3_months_start(self):
        start, _ = self._range("Last 3 months")
        assert start == datetime.date(2025, 11, 1)

    def test_last_6_months_start(self):
        start, _ = self._range("Last 6 months")
        assert start == datetime.date(2025, 8, 1)

    def test_last_12_months_start(self):
        start, _ = self._range("Last 12 months")
        assert start == datetime.date(2025, 2, 1)

    def test_all_time_uses_min_max(self):
        start, end = self._range("All time")
        assert start == self.MIN_DATE
        assert end   == self.MAX_DATE

    def test_clamped_to_min_date(self):
        """If the computed start is before min_date, clamp to min_date."""
        start, _ = compute_date_range(
            "Last 12 months",
            datetime.date(2024, 6, 15),   # today
            datetime.date(2024, 5, 1),    # min_date much later than 12mo ago
            datetime.date(2024, 6, 15),
        )
        assert start == datetime.date(2024, 5, 1)

    def test_last_month_across_year_boundary(self):
        """Jan 2026 — last month should be December 2025."""
        today = datetime.date(2026, 1, 15)
        start, end = compute_date_range("Last month", today,
                                        datetime.date(2024, 1, 1),
                                        datetime.date(2026, 1, 15))
        assert start == datetime.date(2025, 12, 1)
        assert end   == datetime.date(2025, 12, 31)


# ── detect_subscriptions ──────────────────────────────────────────────────────

class TestDetectSubscriptions:
    def test_detects_monthly_subscription(self):
        rows = [
            {"Date": "2025-01-15", "Description": "Netflix", "Amount": 15.99, "Category": "Entertainment", "Card": "Chase"},
            {"Date": "2025-02-15", "Description": "Netflix", "Amount": 15.99, "Category": "Entertainment", "Card": "Chase"},
            {"Date": "2025-03-15", "Description": "Netflix", "Amount": 15.99, "Category": "Entertainment", "Card": "Chase"},
        ]
        subs = detect_subscriptions(make_df(rows))
        assert len(subs) == 1
        assert subs.iloc[0]["Merchant"] == "Netflix"
        assert subs.iloc[0]["Cadence"] == "Monthly"

    def test_ignores_merchant_with_one_occurrence(self):
        rows = [
            {"Date": "2025-01-15", "Description": "One-Time Purchase", "Amount": 50.0, "Category": "Shopping", "Card": "Chase"},
        ]
        subs = detect_subscriptions(make_df(rows))
        assert subs.empty

    def test_ignores_irregular_charges(self):
        """Wildly varying amounts should not be flagged as subscriptions."""
        rows = [
            {"Date": "2025-01-15", "Description": "Irregular Co", "Amount": 10.00, "Category": "Other", "Card": "Chase"},
            {"Date": "2025-02-15", "Description": "Irregular Co", "Amount": 95.00, "Category": "Other", "Card": "Chase"},
            {"Date": "2025-03-15", "Description": "Irregular Co", "Amount": 10.00, "Category": "Other", "Card": "Chase"},
        ]
        subs = detect_subscriptions(make_df(rows))
        assert subs.empty

    def test_detects_annual_subscription(self):
        rows = [
            {"Date": "2024-01-10", "Description": "Amazon Prime", "Amount": 139.0, "Category": "Shopping", "Card": "Chase"},
            {"Date": "2025-01-10", "Description": "Amazon Prime", "Amount": 139.0, "Category": "Shopping", "Card": "Chase"},
        ]
        subs = detect_subscriptions(make_df(rows))
        assert len(subs) == 1
        assert subs.iloc[0]["Cadence"] == "Annual"

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["Date", "Description", "Amount", "Category", "Card", "YearMonth"])
        subs = detect_subscriptions(df)
        assert subs.empty


# ── compute_insights ──────────────────────────────────────────────────────────

class TestComputeInsights:
    def test_returns_empty_for_single_month(self):
        rows = [
            {"Date": "2025-01-10", "Description": "Target", "Amount": 50.0, "Category": "Shopping", "Card": "Chase"},
        ]
        assert compute_insights(make_df(rows)) == []

    def test_returns_empty_for_empty_df(self):
        df = pd.DataFrame(columns=["Date", "Description", "Amount", "Category", "Card", "YearMonth"])
        assert compute_insights(df) == []

    def test_detects_category_spike(self):
        """Dining doubles in the current month vs the prior 3 — should surface as spike."""
        rows = []
        for month in ["2025-10", "2025-11", "2025-12"]:
            rows.append({"Date": f"{month}-15", "Description": "Restaurant", "Amount": 200.0,
                         "Category": "Dining", "Card": "Chase"})
        # Current month — doubled
        rows.append({"Date": "2026-01-15", "Description": "Restaurant", "Amount": 400.0,
                     "Category": "Dining", "Card": "Chase"})

        insights = compute_insights(make_df(rows))
        dining = [i for i in insights if i["category"] == "Dining"]
        assert len(dining) == 1
        assert dining[0]["indicator"] == "spike"

    def test_detects_category_drop(self):
        """A category that halves should surface as a drop."""
        rows = []
        for month in ["2025-10", "2025-11", "2025-12"]:
            rows.append({"Date": f"{month}-15", "Description": "Gym", "Amount": 100.0,
                         "Category": "Health", "Card": "Chase"})
        rows.append({"Date": "2026-01-15", "Description": "Gym", "Amount": 30.0,
                     "Category": "Health", "Card": "Chase"})

        insights = compute_insights(make_df(rows))
        health = [i for i in insights if i["category"] == "Health"]
        assert len(health) == 1
        assert health[0]["indicator"] == "drop"

    def test_ignores_small_changes(self):
        """A 5% change below the $25 threshold should not appear."""
        rows = []
        for month in ["2025-10", "2025-11", "2025-12"]:
            rows.append({"Date": f"{month}-15", "Description": "Coffee", "Amount": 20.0,
                         "Category": "Dining", "Card": "Chase"})
        rows.append({"Date": "2026-01-15", "Description": "Coffee", "Amount": 21.0,
                     "Category": "Dining", "Card": "Chase"})

        insights = compute_insights(make_df(rows))
        dining = [i for i in insights if i["category"] == "Dining" and i["type"] == "category"]
        assert len(dining) == 0

    def test_returns_at_most_5(self):
        """Insights are capped at 5."""
        rows = []
        categories = ["Dining", "Shopping", "Travel", "Health", "Entertainment", "Utilities"]
        for month in ["2025-10", "2025-11", "2025-12"]:
            for cat in categories:
                rows.append({"Date": f"{month}-15", "Description": cat, "Amount": 100.0,
                             "Category": cat, "Card": "Chase"})
        for cat in categories:
            rows.append({"Date": "2026-01-15", "Description": cat, "Amount": 300.0,
                         "Category": cat, "Card": "Chase"})

        insights = compute_insights(make_df(rows))
        assert len(insights) <= 5


# ── _get_config ───────────────────────────────────────────────────────────────

class TestGetConfig:
    def test_exact_match_returns_that_config(self):
        cfg = _get_config("checking")
        assert cfg["is_checking"] is True

    def test_substring_match_returns_checking(self):
        """Any filename containing 'checking' should use the checking config."""
        cfg = _get_config("chase_checking_2024")
        assert cfg["is_checking"] is True

    def test_unknown_key_falls_back_to_default(self):
        cfg = _get_config("freedom_unlimited")
        assert cfg["is_checking"] is False
        assert cfg["amount_sign"] == -1

    def test_default_key_returns_default(self):
        cfg = _get_config("default")
        assert cfg["is_checking"] is False


# ── _load_checking ────────────────────────────────────────────────────────────

def make_checking_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal Chase checking DataFrame."""
    df = pd.DataFrame(rows)
    df["Posting Date"] = pd.to_datetime(df["Posting Date"])
    return df


class TestLoadChecking:
    CFG = CARD_CONFIG["checking"]

    def test_credit_row_is_income(self):
        raw = make_checking_df([{
            "Posting Date": "2025-01-15", "Description": "Direct Deposit",
            "Amount": 2500.00, "Details": "Credit",
        }])
        df = _load_checking(raw, "Checking", self.CFG)
        assert len(df) == 1
        assert df.iloc[0]["RecordType"] == "income"
        assert df.iloc[0]["Category"] == "Income"
        assert df.iloc[0]["Amount"] == 2500.00

    def test_debit_row_is_expense(self):
        raw = make_checking_df([{
            "Posting Date": "2025-01-20", "Description": "Grocery Store",
            "Amount": -45.00, "Details": "Debit",
        }])
        df = _load_checking(raw, "Checking", self.CFG)
        assert len(df) == 1
        assert df.iloc[0]["RecordType"] == "expense"
        assert df.iloc[0]["Category"] == "Uncategorized"
        assert df.iloc[0]["Amount"] == 45.00   # absolute value

    def test_cc_autopay_is_excluded(self):
        raw = make_checking_df([{
            "Posting Date": "2025-01-25", "Description": "Autopay Chase Card",
            "Amount": -1200.00, "Details": "Debit",
        }])
        df = _load_checking(raw, "Checking", self.CFG)
        assert df.empty

    def test_cc_payment_thank_you_is_excluded(self):
        raw = make_checking_df([{
            "Posting Date": "2025-01-25", "Description": "Payment Thank You",
            "Amount": -800.00, "Details": "Debit",
        }])
        df = _load_checking(raw, "Checking", self.CFG)
        assert df.empty

    def test_online_payment_is_excluded(self):
        raw = make_checking_df([{
            "Posting Date": "2025-02-01", "Description": "Online Payment",
            "Amount": -500.00, "Details": "Debit",
        }])
        df = _load_checking(raw, "Checking", self.CFG)
        assert df.empty

    def test_mixed_rows_all_handled(self):
        """Income, normal expense, and CC payment — only first two make it through."""
        raw = make_checking_df([
            {"Posting Date": "2025-01-10", "Description": "Payroll",        "Amount":  3000.00, "Details": "Credit"},
            {"Posting Date": "2025-01-15", "Description": "Coffee Shop",    "Amount":   -12.50, "Details": "Debit"},
            {"Posting Date": "2025-01-20", "Description": "Autopay Chase",  "Amount": -1100.00, "Details": "Debit"},
        ])
        df = _load_checking(raw, "Checking", self.CFG)
        assert len(df) == 2
        assert df[df["RecordType"] == "income"]["Amount"].iloc[0]  == 3000.00
        assert df[df["RecordType"] == "expense"]["Amount"].iloc[0] == 12.50

    def test_empty_input_returns_empty_with_columns(self):
        raw = pd.DataFrame(columns=["Posting Date", "Description", "Amount", "Details"])
        df = _load_checking(raw, "Checking", self.CFG)
        assert df.empty
        assert "RecordType" in df.columns
        assert "Amount" in df.columns

    def test_amount_is_always_positive(self):
        """Stored Amount should be the absolute value regardless of CSV sign."""
        raw = make_checking_df([
            {"Posting Date": "2025-01-10", "Description": "Deposit",  "Amount":  500.00, "Details": "Credit"},
            {"Posting Date": "2025-01-15", "Description": "Transfer", "Amount": -200.00, "Details": "Debit"},
        ])
        df = _load_checking(raw, "Checking", self.CFG)
        assert (df["Amount"] >= 0).all()
