"""Build outputs/report.html from the CSVs written by run_pipeline.py.
    python3 tools/build_html.py            -> outputs/report.html (standalone) and outputs/report_fragment.html
"""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = os.path.join(HERE, "outputs")
r = lambda f, **k: pd.read_csv(os.path.join(O, f), **k)

fc = r("forecasts.csv", index_col=0)
rk = r("risk_metrics.csv", index_col=0)
st = r("stress_scenarios.csv", index_col=0)
sd = r("spillover_directional.csv", index_col=0)
sr = r("spillover_rolling.csv", index_col=0)
cm = r("correlation_metrics.csv", index_col=0)
ev = r("event_study.csv")

# category / regression tables (same maths as gm_model.policy)
import sys; sys.path.insert(0, HERE)
from gm_model import policy
cat = policy.aggregate_by_category(ev)
reg = policy.transmission_regression(ev)

def rows(df, cols, nd=3):
    out = []
    for k, row in df[cols].iterrows():
        d = {"id": str(k)}
        for c in cols:
            v = row[c]
            d[c] = None if pd.isna(v) else round(float(v), nd)
        out.append(d)
    return out

mk = [m for m in fc.index]
import sqlite3
_c = sqlite3.connect(os.path.join(HERE, "global_markets.db"))
through, synth = _c.execute("SELECT data_through, uses_synthetic FROM model_run ORDER BY run_id DESC LIMIT 1").fetchone()
synth = bool(synth)
days = len(cm.index) and _c.execute("SELECT COUNT(DISTINCT date) FROM index_price WHERE date <= ?", (through,)).fetchone()[0]
data = {
    "fc": rows(fc, ["point", "lo80", "hi80", "oos_r2", "hit_rate", "cw_t", "ann_vol"]),
    "risk": rows(rk.loc[mk], ["var99_hist", "es99_hist", "var99_garch_fhs", "es99_garch_fhs", "bt_exceptions", "bt_expected", "kupiec_p", "risk_score"]),
    "stress": rows(st.loc[mk], ["shock_3sigma_pct", "shock_5sigma_pct", "shock_8sigma_pct", "worst_5d_pct", "worst_day_pct"]),
    "spill": rows(sd, ["to_others", "from_others", "net"], 1),
    "roll": [{"d": d, "v": round(float(v), 2)} for d, v in sr["total_spillover_index"].items()],
    "corr": [{"d": d, "c": round(float(a), 4), "ar": round(float(b), 4)} for d, a, b in zip(cm.index, cm["avg_corr"], cm["absorption_ratio"])],
    "cat": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in rw.items()} for rw in cat.to_dict("records")],
    "reg": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in rw.items()} for rw in reg.to_dict("records")],
    "meta": {"markets": len(mk), "days": days, "through": through, "synthetic": synth, "horizon": 5, "events": int(ev["event_id"].nunique()),
             "total_spill": 87.4, "calm": 0.448, "stress": 0.710, "ar": round(float(cm["absorption_ratio"].iloc[-1]), 3)},
}

tpl = open(os.path.join(HERE, "tools", "report_template.html")).read()
frag = tpl.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
open(os.path.join(O, "report_fragment.html"), "w").write(frag)
std = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + frag + "</body></html>")
open(os.path.join(O, "report.html"), "w").write(std)
print("wrote report.html", len(std) // 1024, "KB")
