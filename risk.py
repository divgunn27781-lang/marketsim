"""Risk measurement: VaR / expected shortfall, backtesting, stress tests and a composite score.

Returns are in PERCENT. VaR and ES are reported as positive loss percentages.
"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import xlogy

from .forecast import garch11_fit, garch_filter


# ------------------------------------------------------------------ point estimates
def hist_var_es(r, level=0.99):
    r = np.asarray(r, float)
    q = np.quantile(r, 1 - level)
    return -q, -r[r <= q].mean()


def normal_var_es(r, level=0.99):
    mu, sd = np.mean(r), np.std(r, ddof=1)
    z = stats.norm.ppf(1 - level)
    return -(mu + sd * z), -(mu - sd * stats.norm.pdf(z) / (1 - level))


def student_t_var_es(r, level=0.99):
    df, loc, scale = stats.t.fit(np.asarray(r, float))
    df = max(df, 2.1)
    q = stats.t.ppf(1 - level, df)
    var = -(loc + scale * q)
    es_std = (stats.t.pdf(q, df) / (1 - level)) * (df + q ** 2) / (df - 1)
    return var, -(loc - scale * es_std)


def fhs_var_es(r, level=0.99, fit=None):
    """Filtered historical simulation: GARCH volatility scaling of empirical standardised residuals."""
    fit = fit or garch11_fit(r)
    z = fit["e"] / np.sqrt(fit["h"])
    qz = np.quantile(z, 1 - level)
    sig = np.sqrt(fit["h_next"])
    return -(fit["mu"] + sig * qz), -(fit["mu"] + sig * z[z <= qz].mean())


def max_drawdown(r):
    cum = np.cumsum(np.asarray(r, float) / 100)
    peak = np.maximum.accumulate(cum)
    return float(100 * (1 - np.exp((cum - peak).min())))


# ------------------------------------------------------------------ backtests
def kupiec_pof(exceptions, p):
    x, n = int(np.sum(exceptions)), len(exceptions)
    pi = x / n
    ll0 = xlogy(n - x, 1 - p) + xlogy(x, p)
    ll1 = xlogy(n - x, 1 - pi) + xlogy(x, pi)
    lr = -2 * (ll0 - ll1)
    return lr, 1 - stats.chi2.cdf(lr, 1)


def christoffersen_ind(exceptions):
    e = np.asarray(exceptions, int)
    n00 = np.sum((e[:-1] == 0) & (e[1:] == 0)); n01 = np.sum((e[:-1] == 0) & (e[1:] == 1))
    n10 = np.sum((e[:-1] == 1) & (e[1:] == 0)); n11 = np.sum((e[:-1] == 1) & (e[1:] == 1))
    pi01 = n01 / max(n00 + n01, 1); pi11 = n11 / max(n10 + n11, 1)
    pi = (n01 + n11) / max(n00 + n01 + n10 + n11, 1)
    ll0 = xlogy(n00 + n10, 1 - pi) + xlogy(n01 + n11, pi)
    ll1 = (xlogy(n00, 1 - pi01) + xlogy(n01, pi01) + xlogy(n10, 1 - pi11) + xlogy(n11, pi11))
    lr = -2 * (ll0 - ll1)
    return lr, 1 - stats.chi2.cdf(lr, 1)


def rolling_garch_var(r, level=0.99, window=750, refit=21):
    """Out-of-sample one-day VaR series: parameters re-estimated every `refit` days on a trailing window;
    in between only the variance filter is updated (no look-ahead)."""
    r = np.asarray(r, float)
    var = np.full(len(r), np.nan)
    for s in range(window, len(r), refit):
        fit = garch11_fit(r[s - window:s])
        hist = r[s - window:min(s + refit, len(r))]
        h = garch_filter(hist - fit["mu"], fit["omega"], fit["alpha"], fit["beta"], fit["v0"])
        qz = np.quantile(fit["e"] / np.sqrt(fit["h"]), 1 - level)
        blk = slice(window, window + min(refit, len(r) - s))
        var[s:s + (blk.stop - blk.start)] = -(fit["mu"] + np.sqrt(h[blk]) * qz)
    return var


def backtest_var(r, level=0.99, window=750, refit=21):
    r = np.asarray(r, float)
    var = rolling_garch_var(r, level, window, refit)
    m = ~np.isnan(var)
    exc = (r[m] < -var[m]).astype(int)
    p = 1 - level
    lr_u, p_u = kupiec_pof(exc, p)
    lr_i, p_i = christoffersen_ind(exc)
    return {"n": int(m.sum()), "exceptions": int(exc.sum()), "expected": p * m.sum(),
            "kupiec_p": p_u, "christoffersen_p": p_i}


# ------------------------------------------------------------------ stress testing
def tail_betas(R, quantile=0.10):
    """Beta of each market to the equal-weight global return, in all states and in the global-tail state."""
    rows = {}
    for c in R.columns:
        g = R.drop(columns=[c]).mean(axis=1)
        d = pd.concat([R[c], g], axis=1).dropna()
        y, x = d.iloc[:, 0].values, d.iloc[:, 1].values
        beta = np.cov(y, x)[0, 1] / x.var(ddof=1)
        tail = x <= np.quantile(x, quantile)
        tbeta = np.cov(y[tail], x[tail])[0, 1] / x[tail].var(ddof=1)
        rows[c] = {"beta": beta, "tail_beta": tbeta, "global_sigma": x.std(ddof=1)}
    return pd.DataFrame(rows).T


def stress_scenarios(R, shocks=(-3.0, -5.0, -8.0), quantile=0.10):
    """Global-factor shock scenarios, expressed in multiples of the global daily sigma, transmitted
    with tail betas. Also reports the worst historical 5-day window per market."""
    tb = tail_betas(R, quantile)
    out = pd.DataFrame(index=R.columns)
    gs = tb["global_sigma"].mean()
    for s in shocks:
        out[f"shock_{abs(s):g}sigma_pct"] = tb["tail_beta"] * s * gs
    out["worst_5d_pct"] = R.rolling(5).sum().min()
    out["worst_day_pct"] = R.min()
    return out, tb


def composite_risk_score(R, es99, tb):
    """0-100 percentile-rank composite of volatility, tail loss, drawdown, tail beta and correlation."""
    recent = R.tail(250)
    corr = recent.corr()
    avg_corr = (corr.sum() - 1) / (len(corr) - 1)
    parts = pd.DataFrame({
        "ann_vol": R.std() * np.sqrt(252),
        "es99": es99,
        "max_drawdown": pd.Series({c: max_drawdown(R[c].dropna().values) for c in R.columns}),
        "tail_beta": tb["tail_beta"],
        "avg_corr_250d": avg_corr,
    })
    score = parts.rank(pct=True).mean(axis=1) * 100
    return score, parts
