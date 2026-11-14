"""Policy-event analysis: market-model event study and policy-transmission regressions.

Returns are in PERCENT. For each event the market model r_i = a + b * m is estimated on days
[-250, -30] relative to the event, where m is the equal-weighted return of all markets OUTSIDE
the event country (so the event does not contaminate its own benchmark).
"""
import numpy as np
import pandas as pd
from scipy import stats

EST = (-250, -30)
WINDOWS = {"m1_p1": (-1, 1), "0_p5": (0, 5)}


def event_study(R, events, exchanges):
    """events: DataFrame with event_id, event_date, country, category, surprise_bp.
    exchanges: DataFrame with code, country. Returns one row per (event, affected exchange)."""
    by_country = exchanges.groupby("country")["code"].apply(list).to_dict()
    idx = R.index
    rows = []
    for ev in events.itertuples():
        affected = [c for c in by_country.get(ev.country, []) if c in R.columns]
        if not affected:
            continue
        pos = int(idx.searchsorted(pd.Timestamp(ev.event_date)))
        if pos + max(w[1] for w in WINDOWS.values()) >= len(idx) or pos + EST[0] < 0:
            continue
        market = R.drop(columns=affected).mean(axis=1)
        est = slice(pos + EST[0], pos + EST[1] + 1)
        for c in affected:
            y_est, x_est = R[c].iloc[est].values, market.iloc[est].values
            ok = ~np.isnan(y_est) & ~np.isnan(x_est)
            if ok.sum() < 100:
                continue
            b = np.cov(y_est[ok], x_est[ok])[0, 1] / x_est[ok].var(ddof=1)
            a = y_est[ok].mean() - b * x_est[ok].mean()
            resid = y_est[ok] - (a + b * x_est[ok])
            sigma = resid.std(ddof=2)
            row = {"event_id": ev.event_id, "event_date": ev.event_date, "country": ev.country,
                   "category": ev.category, "surprise_bp": ev.surprise_bp, "code": c}
            for name, (lo, hi) in WINDOWS.items():
                sl = slice(pos + lo, pos + hi + 1)
                ar = R[c].iloc[sl].values - (a + b * market.iloc[sl].values)
                car = float(ar.sum())
                row[f"car_{name}"] = car
                row[f"t_{name}"] = car / (sigma * np.sqrt(len(ar)))
            rows.append(row)
    return pd.DataFrame(rows)


def aggregate_by_category(res):
    """Average CARs per event first (avoids double counting two exchanges in one country), then test
    the cross-event mean per policy category."""
    ev = res.groupby(["event_id", "category"], as_index=False)[["car_m1_p1", "car_0_p5"]].mean()
    out = []
    for cat, g in ev.groupby("category"):
        row = {"category": cat, "n_events": len(g)}
        for col in ("car_m1_p1", "car_0_p5"):
            x = g[col].values
            se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan
            row[f"mean_{col}"] = x.mean()
            row[f"t_{col}"] = x.mean() / se if se and se > 0 else np.nan
        out.append(row)
    return pd.DataFrame(out)


def transmission_regression(res):
    """Slope of the announcement-window CAR on the policy surprise (percent return per bp)."""
    ev = res.dropna(subset=["surprise_bp"]).groupby(["event_id", "category"], as_index=False) \
        .agg(car=("car_m1_p1", "mean"), surprise=("surprise_bp", "first"))
    rows = []
    for name, g in [("all", ev)] + [(c, d) for c, d in ev.groupby("category")]:
        if len(g) < 5:
            continue
        lr = stats.linregress(g["surprise"], g["car"])
        rows.append({"group": name, "n": len(g), "slope_pct_per_bp": lr.slope, "stderr": lr.stderr,
                     "r2": lr.rvalue ** 2, "p_value": lr.pvalue})
    return pd.DataFrame(rows)
