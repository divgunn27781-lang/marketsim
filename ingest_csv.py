"""Load real data into the database from CSV files (the hook for licensed/real feeds).

    python3 ingest_csv.py prices  --db global_markets.db --exchange NSE --csv nifty.csv
        CSV columns: date, close                      (daily benchmark levels)
    python3 ingest_csv.py flows   --db global_markets.db --exchange NSE --class 1 --csv fii.csv --unit "INR crore" --source NSDL
        CSV columns: date, net_flow                   (daily net flow; 1 = foreign, 2 = domestic)
    python3 ingest_csv.py events  --db global_markets.db --csv events.csv --source "RBI"
        CSV columns: event_date, country, category, description[, surprise_bp]

Loading real prices for an exchange first deletes that exchange's synthetic rows, so real and
synthetic series are never mixed. Log returns are computed here from consecutive closes.
"""
import argparse
import sqlite3

import numpy as np
import pandas as pd


def _exchange_id(con, code):
    row = con.execute("SELECT exchange_id FROM exchange WHERE code = ?", (code,)).fetchone()
    if row is None:
        raise SystemExit(f"unknown exchange code {code!r}")
    return row[0]


def load_prices(con, code, csv):
    df = pd.read_csv(csv, parse_dates=["date"]).dropna(subset=["close"]).sort_values("date")
    if (df["close"] <= 0).any():
        raise SystemExit("non-positive close found")
    df["log_return"] = np.log(df["close"]).diff()
    eid = _exchange_id(con, code)
    con.execute("DELETE FROM index_price WHERE exchange_id = ? AND is_synthetic = 1", (eid,))
    con.execute("DELETE FROM institutional_flow WHERE exchange_id = ? AND is_synthetic = 1", (eid,))
    rows = [(eid, d.strftime("%Y-%m-%d"), float(c), None if np.isnan(r) else float(r))
            for d, c, r in zip(df["date"], df["close"], df["log_return"])]
    con.executemany("INSERT OR REPLACE INTO index_price(exchange_id, date, close, log_return, is_synthetic)"
                    " VALUES (?,?,?,?,0)", rows)
    return len(rows)


def load_flows(con, code, cls, csv, unit, source):
    df = pd.read_csv(csv, parse_dates=["date"])
    eid = _exchange_id(con, code)
    rows = [(eid, cls, d.strftime("%Y-%m-%d"), d.strftime("%Y-%m-%d"), "daily", float(v), unit, source)
            for d, v in zip(df["date"], df["net_flow"])]
    con.executemany("INSERT OR REPLACE INTO institutional_flow(exchange_id, class_id, period_start, period_end,"
                    " frequency, net_flow, unit, source, is_synthetic) VALUES (?,?,?,?,?,?,?,?,0)", rows)
    return len(rows)


def load_events(con, csv, source):
    df = pd.read_csv(csv)
    if "surprise_bp" not in df:
        df["surprise_bp"] = np.nan
    rows = [(str(r.event_date)[:10], r.country, r.category, r.description,
             None if pd.isna(r.surprise_bp) else float(r.surprise_bp), source)
            for r in df.itertuples()]
    con.executemany("INSERT INTO policy_event(event_date, country, category, description, surprise_bp, source,"
                    " is_synthetic) VALUES (?,?,?,?,?,?,0)", rows)
    return len(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["prices", "flows", "events"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--exchange")
    ap.add_argument("--class", dest="cls", type=int, default=1)
    ap.add_argument("--unit", default="USD mn")
    ap.add_argument("--source", default="manual import")
    a = ap.parse_args()
    con = sqlite3.connect(a.db)
    con.execute("PRAGMA foreign_keys = ON")
    if a.kind == "prices":
        n = load_prices(con, a.exchange, a.csv)
    elif a.kind == "flows":
        n = load_flows(con, a.exchange, a.cls, a.csv, a.unit, a.source)
    else:
        n = load_events(con, a.csv, a.source)
    con.commit()
    print(f"loaded {n} rows")
