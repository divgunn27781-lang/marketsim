"""Run the full analysis pipeline against the database and write results to the DB, CSVs and a report.

    python3 run_pipeline.py [--db global_markets.db] [--out outputs] [--horizon 5]
"""
import argparse
import datetime as dt
import os

import numpy as np
import pandas as pd

from gm_model import contagion, data, forecast, policy, risk

HERE = os.path.dirname(os.path.abspath(__file__))


def md_table(df, digits=2, index_name=""):
    d = df.copy()
    head = [index_name or (d.index.name or "")] + [str(c) for c in d.columns]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    # columns whose values are all whole numbers (counts) print without decimals
    whole = {c: pd.api.types.is_numeric_dtype(d[c]) and d[c].notna().any() and bool((d[c].dropna() % 1 == 0).all())
             for c in d.columns}
    for i, idx in enumerate(d.index):
        cells = [str(idx)]
        for c in d.columns:
            v = d[c].iloc[i]
            if isinstance(v, (float, np.floating, int, np.integer)):
                if pd.isna(v):
                    cells.append("")
                elif whole[c]:
                    cells.append(f"{int(v)}")
                else:
                    cells.append(f"{v:.{digits}f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run(db, out_dir, horizon=5, include_real_events=False):
    os.makedirs(out_dir, exist_ok=True)
    con = data.connect(db)
    ex = data.exchanges(con)
    R = data.load_returns(con) * 100.0
    if R.shape[1] < 3:
        raise SystemExit("Fewer than 3 exchanges have price history - load data first (ingest_csv.py).")
    synth = data.uses_synthetic(con)
    F, D = data.load_daily_flows(con, 1), data.load_daily_flows(con, 2)
    F, D = (F if not F.empty else None), (D if not D.empty else None)
    ids = dict(zip(ex["code"], ex["exchange_id"]))
    print(f"data: {R.shape[1]} markets, {len(R)} days, {R.index[0].date()} -> {R.index[-1].date()}, synthetic={synth}")

    # ------------------------------------------------------------ forecasts
    print("forecasting ...")
    fc, fits = forecast.run_forecasts(R, F, D, horizon)

    # ------------------------------------------------------------ risk
    print("risk ...")
    ew = R.mean(axis=1)
    series = {c: R[c].dropna().values for c in R.columns}
    series["GLOBAL_EW"] = ew.values
    rows = {}
    for c, r in series.items():
        v95, e95 = risk.hist_var_es(r, 0.95)
        v99, e99 = risk.hist_var_es(r, 0.99)
        vt, et = risk.student_t_var_es(r, 0.99)
        vf, ef = risk.fhs_var_es(r, 0.99, fits.get(c))
        bt = risk.backtest_var(r, 0.99)
        rows[c] = {"var95_hist": v95, "es95_hist": e95, "var99_hist": v99, "es99_hist": e99,
                   "var99_t": vt, "es99_t": et, "var99_garch_fhs": vf, "es99_garch_fhs": ef,
                   "bt_exceptions": bt["exceptions"], "bt_expected": bt["expected"],
                   "kupiec_p": bt["kupiec_p"], "christoffersen_p": bt["christoffersen_p"],
                   "max_drawdown_pct": risk.max_drawdown(r)}
    rk = pd.DataFrame(rows).T
    stress, tb = risk.stress_scenarios(R)
    score, parts = risk.composite_risk_score(R, rk.loc[R.columns, "es99_hist"], tb)
    rk["risk_score"] = score
    stress.loc["GLOBAL_EW", "worst_5d_pct"] = ew.rolling(5).sum().min()
    stress.loc["GLOBAL_EW", "worst_day_pct"] = ew.min()

    # ------------------------------------------------------------ policy events
    print("policy events ...")
    events = data.load_events(con, include_real=include_real_events)
    ev_res = policy.event_study(R, events, ex) if len(events) else pd.DataFrame()
    ev_cat = policy.aggregate_by_category(ev_res) if len(ev_res) else pd.DataFrame()
    ev_reg = policy.transmission_regression(ev_res) if len(ev_res) else pd.DataFrame()

    # ------------------------------------------------------------ contagion
    print("contagion ...")
    sp = contagion.spillover_table(R)
    sp_roll = contagion.rolling_total_spillover(R)
    cm = contagion.rolling_corr_metrics(R)
    regimes = contagion.regime_correlations(R)
    cent = contagion.eigenvector_centrality(R)

    # ------------------------------------------------------------ persist
    cur = con.cursor()
    cur.execute("INSERT INTO model_run(started_at, data_through, uses_synthetic, notes) VALUES (?,?,?,?)",
                (dt.datetime.now().isoformat(timespec="seconds"), str(R.index[-1].date()), int(synth),
                 f"horizon={horizon}d; markets={R.shape[1]}"))
    run_id = cur.lastrowid
    cur.executemany(
        "INSERT INTO forecast_output VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(run_id, ids[c], horizon, r.point, r.lo80, r.hi80, r.oos_r2, r.hit_rate, r.cw_t, int(r.n_oos),
          r.garch_alpha, r.garch_beta, r.ann_vol) for c, r in fc.iterrows()])
    risk_rows = []
    for c in R.columns:
        for m, v in {**rk.loc[c].to_dict(), **stress.loc[c].to_dict(), "beta": tb.loc[c, "beta"],
                     "tail_beta": tb.loc[c, "tail_beta"], "eigenvector_centrality": cent[c],
                     "spill_net": sp["directional"].loc[c, "net"]}.items():
            risk_rows.append((run_id, ids[c], m, None if pd.isna(v) else float(v)))
    cur.executemany("INSERT INTO risk_output VALUES (?,?,?,?)", risk_rows)
    th = sp["theta"]
    cur.executemany("INSERT INTO spillover_output VALUES (?,?,?,?)",
                    [(run_id, ids[j], ids[i], float(th.loc[i, j])) for i in th.index for j in th.columns])
    if len(ev_res):
        cur.executemany(
            "INSERT OR REPLACE INTO event_result VALUES (?,?,?,?,?,?,?)",
            [(run_id, int(r.event_id), ids[r.code], r.car_m1_p1, r.t_m1_p1, r.car_0_p5, r.t_0_p5)
             for r in ev_res.itertuples()])
    con.commit()

    # ------------------------------------------------------------ CSV outputs
    fc.to_csv(os.path.join(out_dir, "forecasts.csv"))
    rk.to_csv(os.path.join(out_dir, "risk_metrics.csv"))
    stress.to_csv(os.path.join(out_dir, "stress_scenarios.csv"))
    th.to_csv(os.path.join(out_dir, "spillover_matrix.csv"))
    sp["directional"].to_csv(os.path.join(out_dir, "spillover_directional.csv"))
    sp_roll.to_csv(os.path.join(out_dir, "spillover_rolling.csv"))
    cm.to_csv(os.path.join(out_dir, "correlation_metrics.csv"))
    ev_res.to_csv(os.path.join(out_dir, "event_study.csv"), index=False)

    # ------------------------------------------------------------ report
    top_tx = sp["directional"].sort_values("net", ascending=False)
    fcp = fc.copy()
    fcp.insert(0, "market", fcp.index)
    lines = []
    A = lines.append
    A("# Global markets model: run report")
    A("")
    if synth:
        A("> **SYNTHETIC DATA.** Prices, flows and policy events in this run are generated by `synthetic.py` "
          "to validate the pipeline. Structure was injected on purpose (volatility regimes, a flow-to-return link, "
          "policy responses). Nothing below describes real markets. Attach real feeds with `ingest_csv.py` and re-run.")
        A("")
    A(f"Run {run_id} | data through {R.index[-1].date()} | {R.shape[1]} markets | {len(R):,} daily observations | "
      f"forecast horizon {horizon} trading days")
    A("")
    A("## 1. Return and volatility forecasts")
    A(f"Walk-forward ridge model (no look-ahead). `oos_r2` is relative to an expanding historical-mean benchmark; "
      f"`cw_t` is the Clark-West statistic (about 1.65 or above rejects 'no predictability' at 5%, one-sided). "
      f"Returns in %.")
    view = fc[["point", "lo80", "hi80", "oos_r2", "hit_rate", "cw_t", "ann_vol"]].astype(float)
    A(md_table(view.sort_values("oos_r2", ascending=False), 3, "market"))
    A("")
    A(f"Markets with positive OOS R^2: {int((fc['oos_r2'] > 0).sum())} of {len(fc)}; "
      f"median hit rate {fc['hit_rate'].median():.3f}.")
    A("")
    A("## 2. Risk (one-day, % of index value)")
    A("Backtest is a rolling 750-day GARCH-FHS 99% VaR; Kupiec tests exception frequency, Christoffersen tests "
      "independence (p below 0.05 means the model is rejected).")
    A(md_table(rk[["var99_hist", "es99_hist", "var99_garch_fhs", "es99_garch_fhs", "bt_exceptions", "bt_expected",
                   "kupiec_p", "christoffersen_p", "risk_score"]].sort_values("risk_score", ascending=False), 2, "market"))
    A("")
    A("### Stress scenarios (global shock transmitted with tail betas)")
    A(md_table(stress.sort_values(stress.columns[1]), 2, "market"))
    A("")
    A("## 3. Contagion")
    A(f"- Diebold-Yilmaz total spillover index (VAR(1), 10-day horizon): **{sp['total_index']:.1f}%**")
    A(f"- Average pairwise correlation: calm days {regimes['calm']['avg_corr']:.3f} ({regimes['calm']['days']} days) vs "
      f"stress days {regimes['stress']['avg_corr']:.3f} ({regimes['stress']['days']} days)")
    A(f"- Latest absorption ratio (top {max(1, round(R.shape[1] / 5))} eigenvectors): {cm['absorption_ratio'].iloc[-1]:.3f}")
    A("")
    A("Net transmitters (top 5) and net receivers (bottom 5):")
    A(md_table(pd.concat([top_tx.head(5), top_tx.tail(5)]), 2, "market"))
    A("")
    A("## 4. Policy events")
    if len(ev_res):
        A(f"{ev_res['event_id'].nunique()} events analysed (market-model event study).")
        A(md_table(ev_cat.set_index("category"), 3, "category"))
        A("")
        A("Transmission regression: CAR(-1,+1) in % per basis point of surprise.")
        A(md_table(ev_reg.set_index("group"), 4, "group"))
        if synth:
            A("")
            A("Injected truth for validation: -0.04 %/bp on day 0 plus 30% persistence on day 1, i.e. about "
              "-0.052 %/bp over (-1,+1) for the affected market. US events also leak to every other market, which "
              "contaminates the benchmark and attenuates their estimated effect.")
    else:
        A("No events with analysable price history. Real events are in `policy_event`; they need real price data.")
    A("")
    A("## 5. Limitations")
    A("- Same-day closes are used for all markets; time-zone asynchrony is not corrected (see `contagion.py`).")
    A("- GARCH is Gaussian quasi-MLE; fat tails are handled via filtered historical simulation, not a t-likelihood.")
    A("- Overlapping 5-day targets make naive R^2 significance misleading; the Clark-West statistic uses Newey-West errors.")
    A("- Hedge fund, private equity and investment banking aggregates are stored for context but do not yet "
      "feed the return model (no time series long enough).")
    with open(os.path.join(out_dir, "report.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    con.close()
    return {"run_id": run_id, "forecasts": fc, "risk": rk, "spillover": sp, "events": ev_res, "regimes": regimes,
            "event_cat": ev_cat, "event_reg": ev_reg}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(HERE, "global_markets.db"))
    ap.add_argument("--out", default=os.path.join(HERE, "outputs"))
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--include-real-events", action="store_true")
    a = ap.parse_args()
    res = run(a.db, a.out, a.horizon, a.include_real_events)
    print("done: run", res["run_id"], "->", a.out)
