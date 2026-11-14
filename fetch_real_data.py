"""Download real daily index closes for the 25 benchmarks and load them into the database.

    python3 build_db.py --no-synthetic        # start from reference data only
    python3 fetch_real_data.py                # fetch + ingest (needs open internet)
    python3 run_pipeline.py --include-real-events

Source: Yahoo Finance chart endpoint (unofficial, no API key, personal/research use; check its terms before
anything commercial). For licensed production use, replace this with your vendor feed and keep ingest_csv.py.
Markets that fail to download are skipped and listed; the models need at least 3 markets with 500+ days.
"""
import argparse, csv, datetime as dt, json, os, sqlite3, sys, time, urllib.request

import ingest_csv

HERE = os.path.dirname(os.path.abspath(__file__))
SYMBOLS = {
    "NYSE": "^NYA", "NASDAQ": "^IXIC", "SSE": "000001.SS", "SZSE": "399001.SZ", "JPX": "^N225", "HKEX": "^HSI",
    "EURONEXT": "^N100", "NSE": "^NSEI", "BSE": "^BSESN", "TMX": "^GSPTSE", "LSE": "^FTSE", "DB": "^GDAXI",
    "SIX": "^SSMI", "KRX": "^KS11", "TWSE": "^TWII", "ASX": "^AXJO", "B3": "^BVSP", "TADAWUL": "^TASI.SR",
    "JSE": "^J203.JO", "SGX": "^STI", "BME": "^IBEX", "IDX": "^JKSE", "BMV": "^MXX", "NORDIC": "^OMXS30",
    "BURSA": "^KLSE",
}
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=history"


def parse_chart(payload):
    """Yahoo chart JSON -> list of (YYYY-MM-DD, close). Skips null closes; uses the exchange-local date."""
    res = payload["chart"]["result"][0]
    off = res.get("meta", {}).get("gmtoffset", 0)
    ts, close = res["timestamp"], res["indicators"]["quote"][0]["close"]
    out = {}
    for t, c in zip(ts, close):
        if c is None or c <= 0:
            continue
        out[(dt.datetime.utcfromtimestamp(t + off)).strftime("%Y-%m-%d")] = float(c)
    return sorted(out.items())


def fetch(sym, start, end, tries=3):
    p1 = int(dt.datetime.strptime(start, "%Y-%m-%d").timestamp()); p2 = int(end.timestamp())
    req = urllib.request.Request(URL.format(sym=urllib.request.quote(sym), p1=p1, p2=p2),
                                 headers={"User-Agent": "Mozilla/5.0 (research script)"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return parse_chart(json.load(r))
        except Exception as exc:                      # noqa: BLE001
            err = exc; time.sleep(2 * (k + 1))
    raise RuntimeError(f"{sym}: {err}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(HERE, "global_markets.db"))
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--events", default=os.path.join(HERE, "data", "policy_events.csv"))
    a = ap.parse_args()
    os.makedirs(os.path.join(HERE, "data", "real"), exist_ok=True)
    con = sqlite3.connect(a.db); con.execute("PRAGMA foreign_keys = ON")
    ok, failed = [], []
    for code, sym in SYMBOLS.items():
        try:
            rows = fetch(sym, a.start, dt.datetime.now(dt.timezone.utc))
            path = os.path.join(HERE, "data", "real", f"{code}.csv")
            with open(path, "w", newline="") as fh:
                w = csv.writer(fh); w.writerow(["date", "close"]); w.writerows(rows)
            n = ingest_csv.load_prices(con, code, path)
            ok.append((code, n, rows[0][0], rows[-1][0])); print(f"ok   {code:9s} {n:5d} rows {rows[0][0]} -> {rows[-1][0]}")
        except Exception as exc:                      # noqa: BLE001
            failed.append(code); print(f"FAIL {code:9s} {exc}", file=sys.stderr)
        time.sleep(0.5)
    if os.path.exists(a.events):
        print("events:", ingest_csv.load_events(con, a.events, "public record (dates only, no surprise size)"))
    con.commit()
    print(f"\nloaded {len(ok)}/{len(SYMBOLS)} markets; failed: {failed or 'none'}")
    if len(ok) < 3:
        sys.exit("fewer than 3 markets loaded - cannot run the models")
