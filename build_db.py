"""Build the global markets SQLite database.

    python3 build_db.py                      # reference data + synthetic series (for pipeline validation)
    python3 build_db.py --no-synthetic       # reference data only (attach real feeds with ingest_csv.py)
"""
import argparse
import os
import sqlite3

import numpy as np

import reference_data as ref
import synthetic

HERE = os.path.dirname(os.path.abspath(__file__))


def build(db_path, with_synthetic=True, seed=42):
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript(open(os.path.join(HERE, "schema.sql")).read())
    cur = con.cursor()

    # ---- exchanges
    ex_rows = [(i + 1,) + row for i, row in enumerate(ref.EXCHANGES)]
    cur.executemany(
        "INSERT INTO exchange(exchange_id, code, name, operator, country, region, mic, currency, timezone,"
        " benchmark_index, is_emerging) VALUES (?,?,?,?,?,?,?,?,?,?,?)", ex_rows)
    ex_id = {r[1]: r[0] for r in ex_rows}
    cur.executemany("INSERT INTO investor_class VALUES (?,?,?)", ref.INVESTOR_CLASSES)

    # ---- sourced reference data
    cur.executemany(
        "INSERT INTO exchange_stat(exchange_id, as_of, metric, value, unit, source, source_url, confidence, note)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        [(ex_id[c], a, m, v, u, s, url, conf, n) for c, a, m, v, u, s, url, conf, n in ref.EXCHANGE_STATS])
    cur.executemany(
        "INSERT INTO institutional_flow(exchange_id, class_id, period_start, period_end, frequency, net_flow,"
        " unit, source, source_url, is_synthetic) VALUES (?,?,?,?,?,?,?,?,?,0)",
        [(ex_id[c], k, a, b, f, v, u, s, url) for c, k, a, b, f, v, u, s, url in ref.INDIA_FLOWS])
    cur.executemany(
        "INSERT INTO market_aggregate(scope, name, metric, as_of, value, unit, is_forecast, source, source_url,"
        " confidence, note) VALUES (?,?,?,?,?,?,?,?,?,?,?)", ref.MARKET_AGGREGATES)
    cur.executemany("INSERT INTO alt_manager VALUES (?,?,?,?,?,?,?,?)", ref.ALT_MANAGERS)
    cur.executemany("INSERT INTO ib_league VALUES (?,?,?,?,?,?,?,?)", ref.IB_LEAGUE)
    cur.executemany(
        "INSERT INTO policy_event(event_date, country, category, description, surprise_bp, source, source_url,"
        " is_synthetic) VALUES (?,?,?,?,?,?,?,0)", ref.REAL_POLICY_EVENTS)

    # ---- synthetic series
    if with_synthetic:
        meta = [{"code": r[1], "country": r[4], "region": r[5], "is_emerging": r[10]} for r in ex_rows]
        data = synthetic.generate(meta, seed=seed)
        px, rt = data["prices"], data["returns"]
        rows = []
        for code in px.columns:
            for d, c, r in zip(px.index, px[code].values, rt[code].values):
                rows.append((ex_id[code], d.strftime("%Y-%m-%d"), float(c), float(r)))
        cur.executemany("INSERT INTO index_price(exchange_id, date, close, log_return, is_synthetic)"
                        " VALUES (?,?,?,?,1)", rows)

        flow_rows = []
        for cls, frame in ((1, data["foreign"]), (2, data["domestic"])):
            for code in frame.columns:
                for d, v in zip(frame.index, frame[code].values):
                    ds = d.strftime("%Y-%m-%d")
                    flow_rows.append((ex_id[code], cls, ds, ds, "daily", float(v), "USD mn",
                                      "SYNTHETIC", None))
        cur.executemany(
            "INSERT INTO institutional_flow(exchange_id, class_id, period_start, period_end, frequency,"
            " net_flow, unit, source, source_url, is_synthetic) VALUES (?,?,?,?,?,?,?,?,?,1)", flow_rows)

        cur.executemany(
            "INSERT INTO policy_event(event_date, country, category, description, surprise_bp, source,"
            " source_url, is_synthetic) VALUES (?,?,?,?,?,'SYNTHETIC',NULL,1)",
            [(e["event_date"], e["country"], e["category"], e["description"], e["surprise_bp"])
             for e in data["events"]])

    con.commit()
    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("exchange", "exchange_stat", "index_price", "institutional_flow",
                        "market_aggregate", "alt_manager", "ib_league", "policy_event")}
    con.close()
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(HERE, "global_markets.db"))
    ap.add_argument("--no-synthetic", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    for table, n in build(a.db, not a.no_synthetic, a.seed).items():
        print(f"{table:20s} {n:>8,d}")
    print("wrote", a.db)
