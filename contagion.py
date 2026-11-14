"""Cross-market contagion: correlation regimes, absorption ratio, network centrality and the
Diebold-Yilmaz (2012) generalised forecast-error-variance-decomposition spillover index.

Caveat for real data: markets close at different times, so same-day correlations understate
Asia->Europe->US transmission. The VAR(1) below partly absorbs this through the lag; for production use,
consider lagging Asia-Pacific returns or using synchronised (e.g. 16:00 GMT) price snapshots.
"""
import numpy as np
import pandas as pd


# ------------------------------------------------------------------ correlation structure
def avg_offdiag(C):
    n = C.shape[0]
    return (C.sum() - np.trace(C)) / (n * (n - 1))


def rolling_corr_metrics(R, corr_window=60, ar_window=250, step=5, k=None):
    """Average pairwise correlation (short window) and Kritzman absorption ratio (long window)."""
    X = R.dropna().values
    T, N = X.shape
    k = k or max(1, round(N / 5))
    rows = []
    for t in range(ar_window, T + 1, step):
        C_short = np.corrcoef(X[t - corr_window:t].T)
        C_long = np.corrcoef(X[t - ar_window:t].T)
        ev = np.linalg.eigvalsh(C_long)
        rows.append((R.dropna().index[t - 1], avg_offdiag(C_short), ev[-k:].sum() / N))
    return pd.DataFrame(rows, columns=["date", "avg_corr", "absorption_ratio"]).set_index("date")


def regime_correlations(R, vol_window=21, quantile=0.80):
    """Average pairwise correlation on calm vs high-volatility days of the global equal-weight portfolio."""
    Rn = R.dropna()
    g = Rn.mean(axis=1)
    vol = g.rolling(vol_window).std()
    stress = vol > vol.quantile(quantile)
    out = {}
    for name, mask in (("calm", ~stress & vol.notna()), ("stress", stress)):
        out[name] = {"days": int(mask.sum()), "avg_corr": avg_offdiag(np.corrcoef(Rn[mask].values.T))}
    return out


def eigenvector_centrality(R, window=250):
    """Leading eigenvector of the |correlation| network over the latest window (sums to 1)."""
    C = np.abs(R.dropna().tail(window).corr().values)
    np.fill_diagonal(C, 0)
    vals, vecs = np.linalg.eigh(C)
    v = np.abs(vecs[:, -1])
    return pd.Series(v / v.sum(), index=R.columns)


# ------------------------------------------------------------------ Diebold-Yilmaz spillovers
def var1_ols(Y, ridge=1e-6):
    T, N = Y.shape
    X = np.hstack([np.ones((T - 1, 1)), Y[:-1]])
    P = ridge * np.eye(N + 1)
    P[0, 0] = 0
    B = np.linalg.solve(X.T @ X + P, X.T @ Y[1:])
    U = Y[1:] - X @ B
    Sigma = U.T @ U / (T - 1 - (N + 1))
    return B[1:].T, Sigma


def gfevd(A, Sigma, H=10):
    """Generalised FEVD (Pesaran-Shin) with rows normalised to sum to one. theta[i, j] = share of
    market i's H-step forecast-error variance attributable to shocks in market j."""
    N = A.shape[0]
    num = np.zeros((N, N))
    den = np.zeros(N)
    Phi = np.eye(N)
    for _ in range(H):
        M = Phi @ Sigma
        num += M ** 2
        den += np.einsum("ij,ij->i", M, Phi)
        Phi = A @ Phi
    theta = num / np.diag(Sigma)[None, :] / den[:, None]
    return theta / theta.sum(axis=1, keepdims=True)


def spillover_table(R, H=10):
    Rn = R.dropna()
    A, Sigma = var1_ols(Rn.values)
    th = gfevd(A, Sigma, H)
    N = th.shape[0]
    off = th - np.diag(np.diag(th))
    frm = off.sum(axis=1) * 100          # received from all others
    to = off.sum(axis=0) * 100           # transmitted to all others
    return {"theta": pd.DataFrame(th, index=Rn.columns, columns=Rn.columns),
            "total_index": 100 * off.sum() / N,
            "directional": pd.DataFrame({"to_others": to, "from_others": frm, "net": to - frm}, index=Rn.columns)}


def rolling_total_spillover(R, window=250, step=20, H=10):
    Rn = R.dropna()
    X = Rn.values
    rows = []
    for t in range(window, len(X) + 1, step):
        A, S = var1_ols(X[t - window:t])
        th = gfevd(A, S, H)
        N = th.shape[0]
        rows.append((Rn.index[t - 1], 100 * (th.sum() - np.trace(th)) / N))
    return pd.Series(dict(rows), name="total_spillover_index")
