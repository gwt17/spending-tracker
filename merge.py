"""
merge.py — Run this whenever you add new CSVs to data/.
Merges all exports, removes duplicate transactions, saves data/merged.csv.
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT   = DATA_DIR / "merged.csv"

# Must match the config in app.py — update both if you add a new card format.
CARD_CONFIG = {
    "default": {
        "date_col":    "Transaction Date",
        "desc_col":    "Description",
        "cat_col":     "Category",
        "amount_col":  "Amount",
        "amount_sign": -1,  # negative = expense (Chase standard)
    },
}


def load_card(path: Path) -> pd.DataFrame:
    card_key = path.stem.lower()
    cfg = CARD_CONFIG.get(card_key, CARD_CONFIG["default"])

    raw = pd.read_csv(path)
    raw.columns = raw.columns.str.strip()

    df = pd.DataFrame()
    df["Date"]        = pd.to_datetime(raw[cfg["date_col"]])
    df["Description"] = raw[cfg["desc_col"]].str.strip()
    df["Category"]    = (
        raw[cfg["cat_col"]].str.strip()
        if cfg["cat_col"] in raw.columns
        else "Uncategorized"
    )
    df["Amount"] = raw[cfg["amount_col"]] * cfg["amount_sign"]
    df["Card"]   = path.stem.title()

    # Expenses only
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
        print(f"  {p.name}")

    frames = []
    for p in csvs:
        frame = load_card(p)
        frame["_source"] = p.name  # track which file each row came from
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)

    # Assign a sequence number within each file for identical-looking transactions.
    # e.g. two $3 Target charges on the same day in the same file get seq 0 and 1,
    # so they're treated as distinct and neither gets dropped.
    combined["_seq"] = combined.groupby(
        ["_source", "Date", "Description", "Amount", "Card"]
    ).cumcount()

    before = len(combined)
    # A duplicate is only removed if the same transaction (including seq number)
    # appears across multiple source files — i.e. overlapping export date ranges.
    combined = combined.drop_duplicates(subset=["Date", "Description", "Amount", "Card", "_seq"])
    after  = len(combined)

    combined = combined.drop(columns=["_source", "_seq"])

    combined = combined.sort_values(["Card", "Date"]).reset_index(drop=True)
    combined.to_csv(OUTPUT, index=False)

    print(f"\nTransactions before dedup: {before:,}")
    print(f"Duplicates removed:        {before - after:,}")
    print(f"Final transaction count:   {after:,}")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
