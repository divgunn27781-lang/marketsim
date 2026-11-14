"""Database access helpers returning wide pandas frames (date x exchange code)."""
import sqlite3

import pandas as pd


def connect(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def exchanges(con):
    return pd.read_sql("SELECT * FROM exchange ORDER BY exchange_id", con)


def load_returns(con, min_obs=500):
    """Wide frame of daily log returns; drops exchanges with too little history."""
    df = pd.read_sql(
        "SELECT e.code, p.date, p.log_return FROM index_price p JOIN exchange e USING(exchange_id)"
        " WHERE p.log_return IS NOT NULL", con, parse_dates=["date"])
    wide = df.pivot(index="date", columns="code", values="log_return").sort_index()
    keep = [c for c in wide.columns if wide[c].notna().sum() >= min_obs]
    wide = wide[keep].dropna(how="all")
    # Local holidays: a market that is closed while others trade has a zero return that day. Fill gaps
    # only inside each market's own history so late-starting series are not padded.
    for c in wide.columns:
        first, last = wide[c].first_valid_index(), wide[c].last_valid_index()
        wide.loc[first:last, c] = wide.loc[first:last, c].fillna(0.0)
    return wide


def uses_synthetic(con):
    return bool(con.execute("SELECT COUNT(*) FROM index_price WHERE is_synthetic = 1").fetchone()[0])


def load_daily_flows(con, class_id):
    """Daily net flows for one investor class (1 = foreign, 2 = domestic), wide by exchange code."""
    df = pd.read_sql(
        "SELECT e.code, f.period_start AS date, f.net_flow FROM institutional_flow f JOIN exchange e USING(exchange_id)"
        " WHERE f.frequency = 'daily' AND f.class_id = ?", con, params=(class_id,), parse_dates=["date"])
    if df.empty:
        return pd.DataFrame()
    return df.pivot(index="date", columns="code", values="net_flow").sort_index()


def load_events(con, include_real=False):
    q = "SELECT * FROM policy_event"
    if not include_real:
        q += " WHERE is_synthetic = 1"
    ev = pd.read_sql(q + " ORDER BY event_date", con, parse_dates=["event_date"])
    return ev
