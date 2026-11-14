"""Return and volatility forecasting.

* GARCH(1,1) (Gaussian quasi-MLE, implemented with scipy; no statsmodels/arch dependency)
  for volatility and prediction-interval width.
* Ridge regression, walk-forward (expanding window, refit every 21 days, no look-ahead),
  forecasting the H-day-ahead cumulative return from own-market momentum, volatility, foreign and
  domestic institutional flows and a global-return factor.
* Evaluation against an expanding historical-mean benchmark: out-of-sample R^2, directional hit
  rate and the Clark-West (2007) test for nested models with Newey-West errors.

All returns here are in PERCENT.
"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.signal import lfilter

Z80 = stats.norm.ppf(0.90)


# ------------------------------------------------------------------ GARCH(1,1)
def garch_filter(e, omega, alpha, beta, v0):
    """Conditional variance h_t given information up to t-1 (h_t uses e_{t-1})."""
    x = omega + alpha * np.concatenate([[v0], e[:-1] ** 2])
    h, _ = lfilter([1.0], [1.0, -beta], x, zi=[beta * v0])
    return h


def garch11_fit(r):
    r = np.asarray(r, float)
    v = r.var()
    mu0 = r.mean()

    def nll(p):
        mu, omega, alpha, beta = p
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 0.999:
            return 1e10
        e = r - mu
        h = garch_filter(e, omega, alpha, beta, v)
        if np.any(h <= 0):
            return 1e10
        return 0.5 * np.sum(np.log(h) + e ** 2 / h)

    x0 = np.array([mu0, 0.05 * v, 0.07, 0.88])
    cons = [{"type": "ineq", "fun": lambda p: 0.998 - p[2] - p[3]}]
    bnds = [(-5, 5), (1e-8, None), (1e-6, 0.5), (1e-6, 0.998)]
    res = minimize(nll, x0, method="SLSQP", bounds=bnds, constraints=cons, options={"maxiter": 300})
    if not res.success or not np.isfinite(res.fun):
        res = minimize(nll, x0, method="Nelder-Mead", options={"maxiter": 2000, "xatol": 1e-6, "fatol": 1e-8})
    mu, omega, alpha, beta = res.x
    e = r - mu
    h = garch_filter(e, omega, alpha, beta, v)
    h_next = omega + alpha * e[-1] ** 2 + beta * h[-1]
    return {"mu": mu, "omega": omega, "alpha": alpha, "beta": beta, "h": h, "e": e,
            "h_next": h_next, "v0": v, "converged": bool(res.success)}


def garch_variance_path(fit, horizon):
    """Daily variance forecasts for k = 1..horizon (percent^2)."""
    a_b = fit["alpha"] + fit["beta"]
    V = fit["omega"] / (1.0 - a_b)
    k = np.arange(horizon)
    return V + a_b ** k * (fit["h_next"] - V)


# ------------------------------------------------------------------ features
def _zscore_flow(f, window=60):
    return f / f.rolling(window).std()


def build_features(code, R, F=None, D=None):
    r = R[code]
    others = R.drop(columns=[code])
    X = pd.DataFrame(index=R.index)
    X["r1"] = r
    X["r5"] = r.rolling(5).mean()
    X["r21"] = r.rolling(21).mean()
    X["vol21"] = r.rolling(21).std()
    X["glob5"] = others.mean(axis=1).rolling(5).mean()
    if F is not None and code in F:
        fz = _zscore_flow(F[code].reindex(R.index))
        X["f1"] = fz
        X["f5"] = fz.rolling(5).mean()
    if D is not None and code in D:
        dz = _zscore_flow(D[code].reindex(R.index))
        X["d1"] = dz
        X["d5"] = dz.rolling(5).mean()
    return X


def _ridge(Xs, y, lam):
    ybar = y.mean()
    A = Xs.T @ Xs + lam * np.eye(Xs.shape[1])
    w = np.linalg.solve(A, Xs.T @ (y - ybar))
    return w, ybar


def _fit_predict(Xtr, ytr, Xte, lambdas, val_n=126, gap=5):
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd == 0] = 1.0
    Z = (Xtr - mu) / sd
    best, best_err = lambdas[0], np.inf
    if len(ytr) > 3 * val_n:
        fit_end = len(ytr) - val_n - gap
        for lam in lambdas:
            w, b = _ridge(Z[:fit_end], ytr[:fit_end], lam)
            err = np.mean((ytr[-val_n:] - (b + Z[-val_n:] @ w)) ** 2)
            if err < best_err:
                best, best_err = lam, err
    w, b = _ridge(Z, ytr, best)
    return b + ((Xte - mu) / sd) @ w, ytr.mean()


def newey_west_t(f, lag):
    f = np.asarray(f, float)
    n = len(f)
    m = f.mean()
    u = f - m
    s = u @ u / n
    for k in range(1, lag + 1):
        w = 1 - k / (lag + 1)
        s += 2 * w * (u[k:] @ u[:-k]) / n
    return m / np.sqrt(s / n) if s > 0 else np.nan


def walk_forward(X, y, H, min_train=500, refit=21, lambdas=(10.0, 100.0, 1000.0)):
    """X: (n,k) array, y: (n,) array with NaN where the H-day target is not yet known."""
    n = len(y)
    valid = ~np.isnan(X).any(1) & ~np.isnan(y)
    pred = np.full(n, np.nan)
    bench = np.full(n, np.nan)
    pos = np.arange(n)
    for start in range(min_train, n, refit):
        tr = pos[valid & (pos <= start - H)]
        if len(tr) < 250:
            continue
        te = pos[start:min(start + refit, n)]
        te = te[~np.isnan(X[te]).any(1)]
        if len(te) == 0:
            continue
        p, b = _fit_predict(X[tr], y[tr], X[te], lambdas, gap=H)
        pred[te] = p
        bench[te] = b
    # final forecast from the latest feature row
    last = n - 1
    tr = pos[valid & (pos <= last - H)]
    final, _ = _fit_predict(X[tr], y[tr], X[[last]], lambdas, gap=H)
    return pred, bench, float(final[0])


def forecast_exchange(code, R, F=None, D=None, H=5):
    r = R[code].dropna()
    Rl = R.loc[r.index]
    X = build_features(code, Rl, F, D)
    y = r.rolling(H).sum().shift(-H)
    pred, bench, final = walk_forward(X.values, y.values, H)
    yv = y.values
    m = ~np.isnan(pred) & ~np.isnan(yv)
    out = {"n_oos": int(m.sum())}
    if m.sum() > 100:
        sse_m = np.sum((yv[m] - pred[m]) ** 2)
        sse_b = np.sum((yv[m] - bench[m]) ** 2)
        out["oos_r2"] = 1 - sse_m / sse_b
        out["hit_rate"] = float(np.mean(np.sign(pred[m]) == np.sign(yv[m])))
        f = (yv[m] - bench[m]) ** 2 - ((yv[m] - pred[m]) ** 2 - (bench[m] - pred[m]) ** 2)
        out["cw_t"] = newey_west_t(f, H - 1)
    else:
        out.update(oos_r2=np.nan, hit_rate=np.nan, cw_t=np.nan)

    g = garch11_fit(r.values)
    var_path = garch_variance_path(g, H)
    sigma_h = np.sqrt(var_path.sum())
    out.update(point=final, lo80=final - Z80 * sigma_h, hi80=final + Z80 * sigma_h,
               garch_alpha=g["alpha"], garch_beta=g["beta"],
               ann_vol=float(np.sqrt(252 * garch_variance_path(g, 21).mean())))
    return out, g


def run_forecasts(R, F=None, D=None, H=5):
    """R in percent. Returns (summary DataFrame, dict of GARCH fits)."""
    rows, fits = {}, {}
    for code in R.columns:
        rows[code], fits[code] = forecast_exchange(code, R, F, D, H)
    return pd.DataFrame(rows).T, fits
