"""
merge.py — Run this whenever you add new CSVs to data/.
Merges all exports, removes duplicate transactions, saves data/merged.csv.
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT   = DATA_DIR / "merged.csv"

# Keep in sync with utils.py CARD_CONFIG (merge.py is standalone, can't import utils).
CARD_CONFIG = {
    "default": {                        # Chase credit card (standard)
        "date_col":    "Transaction Date",
        "desc_col":    "Description",
        "cat_col":     "Category",
        "amount_col":  "Amount",
        "amount_sign": -1,
        "is_checking": False,
    },
    "checking": {                       # Chase checking — matches any filename containing "checking"
        "date_col":    "Posting Date",
        "desc_col":    "Description",
        "cat_col":     None,
        "amount_col":  "Amount",
        "amount_sign": 1,
        "is_checking": True,
        "details_col": "Details",
    },
}

CC_PAYMENT_KEYWORDS = ["autopay", "payment thank you", "online payment"]

TRANSFER_KEYWORDS = [
    "schwab", "moneylink", "fidelity", "vanguard", "tdameritrade",
    "e*trade", "etrade", "robinhood", "coinbase", "wealthfront",
    "betterment", "acorns", "stash invest",
]


def _get_config(card_key: str) -> dict:
    if card_key in CARD_CONFIG:
        return CARD_CONFIG[card_key]
    for key, cfg in CARD_CONFIG.items():
        if key != "default" and key in card_key:
            return cfg
    return CARD_CONFIG["default"]


def _load_checking(raw: pd.DataFrame, card_name: str, cfg: dict) -> pd.DataFrame:
    details_col = cfg.get("details_col", "Details")
    rows = []
    for _, r in raw.iterrows():
        desc       = str(r[cfg["desc_col"]]).strip()
        amount_raw = float(r[cfg["amount_col"]])
        details    = str(r.get(details_col, "")).strip().title()
        is_credit  = details == "Credit" or amount_raw > 0

        if not is_credit and any(kw in desc.lower() for kw in CC_PAYMENT_KEYWORDS):
            continue

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


def main():
    csvs = [
        p for p in sorted(DATA_DIR.glob("*.[Cc][Ss][Vv]"))
        if p.name.lower() != "merged.csv"
    ]

    if not csvs:
        print("No CSV files found in data/. Drop your exports there and try again.")
        return

    print(f"Found {len(csvs)} file(s):")
    for p in csvs:
        cfg = _get_config(p.stem.lower())
        kind = "checking" if cfg.get("is_checking") else "credit card"
        print(f"  {p.name}  ({kind})")

    frames = []
    for p in csvs:
        frame = load_card(p)
        frame["_source"] = p.name
        frames.append(frame)
        print(f"  Loaded {len(frame):,} rows from {p.name}")

    combined = pd.concat(frames, ignore_index=True)

    combined["_seq"] = combined.groupby(
        ["_source", "Date", "Description", "Amount", "Card", "RecordType"]
    ).cumcount()

    before = len(combined)
    combined = combined.drop_duplicates(
        subset=["Date", "Description", "Amount", "Card", "RecordType", "_seq"]
    )
    after = len(combined)

    combined = combined.drop(columns=["_source", "_seq"])
    combined = combined.sort_values(["Card", "Date"]).reset_index(drop=True)
    combined.to_csv(OUTPUT, index=False)

    print(f"\nTransactions before dedup: {before:,}")
    print(f"Duplicates removed:        {before - after:,}")
    print(f"Final transaction count:   {after:,}")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
