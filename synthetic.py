"""Synthetic market data generator.

PURPOSE: exercise and validate the modelling pipeline end to end when no licensed data feed
is attached. Every row produced here is flagged is_synthetic = 1 and must never be read as
real market history.

The generator deliberately injects known structure so the models have something to recover:
  * a two-state (calm/stress) global volatility regime shared by all markets,
  * regional factors and market-specific GARCH(1,1) noise,
  * a weak lead-lag link from "informed" foreign flow to next-day returns,
  * policy events with a known linear response to the surprise size.
Because the structure is injected, results on this data validate the *code*, not the markets.
"""
import numpy as np
import pandas as pd

# (global beta, regional beta, idiosyncratic daily vol)
_PROFILE = {
    "Americas": (1.00, 0.20, 0.0050),
    "EMEA": (0.85, 0.35, 0.0055),
    "Asia-Pacific": (0.65, 0.45, 0.0060),
}
_EM_EXTRA_VOL = 0.0020
KAPPA = 0.08          # informed-flow -> next-day return loading, in units of own daily vol
EVENT_BP_COEF = -0.0004   # day-0 return response per bp of hawkish surprise (25bp -> -1%)


def generate(exchanges, start="2021-01-04", end="2026-11-10", seed=42):
    """exchanges: list of dicts with keys code, country, region, is_emerging.
    Returns dict with 'prices', 'flows' (DataFrames) and 'events' (list of dicts)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    T, N = len(dates), len(exchanges)

    # --- global volatility regime and factor
    state = np.zeros(T, dtype=int)
    p_to_stress = {0: 0.015, 1: 0.96}
    for t in range(1, T):
        state[t] = int(rng.random() < p_to_stress[state[t - 1]])
    sig_g = np.where(state == 0, 0.0060, 0.0155)
    G = 0.0003 + sig_g * rng.standard_normal(T)

    regions = sorted({e["region"] for e in exchanges})
    R = {reg: 0.0045 * rng.standard_normal(T) for reg in regions}

    # --- market-specific GARCH(1,1) noise, vectorised over markets
    idio = np.array([_PROFILE[e["region"]][2] + (_EM_EXTRA_VOL if e["is_emerging"] else 0) for e in exchanges])
    alpha, beta = 0.08, 0.90
    omega = idio ** 2 * (1 - alpha - beta)
    h = idio ** 2
    eps = np.zeros((T, N))
    for t in range(T):
        eps[t] = np.sqrt(h) * rng.standard_normal(N)
        h = omega + alpha * eps[t] ** 2 + beta * h

    bg = np.array([_PROFILE[e["region"]][0] * (1.15 if e["is_emerging"] else 1.0) for e in exchanges])
    br = np.array([_PROFILE[e["region"]][1] for e in exchanges])
    reg_mat = np.column_stack([R[e["region"]] for e in exchanges])

    ret = G[:, None] * bg + reg_mat * br + eps

    # --- informed foreign flow shocks drive next-day returns
    u = rng.standard_normal((T, N))
    sd = idio * 1.6
    ret[1:] += KAPPA * sd * u[:-1]

    # --- policy events with a known response
    codes = [e["code"] for e in exchanges]
    by_country = {}
    for i, e in enumerate(exchanges):
        by_country.setdefault(e["country"], []).append(i)
    countries = sorted(by_country)
    n_events = 40
    idx_pool = np.arange(260, T - 10)                 # leave an estimation window before each event
    ev_idx = np.sort(rng.choice(idx_pool, size=n_events, replace=False))
    categories = ["monetary", "fiscal", "regulatory"]
    events = []
    for k, ti in enumerate(ev_idx):
        country = countries[k % len(countries)] if k >= 6 else "US"
        cat = categories[k % 3]
        surprise = float(np.round(rng.uniform(-50, 50), 1))
        shock = EVENT_BP_COEF * surprise
        ex_idx = by_country[country]
        for i in ex_idx:
            ret[ti, i] += shock
            ret[ti + 1, i] += 0.3 * shock
        if country == "US":                             # US events leak to every market
            others = [i for i in range(N) if i not in ex_idx]
            ret[ti, others] += 0.25 * shock
            ret[ti + 1, others] += 0.25 * 0.3 * shock
        events.append({
            "event_date": dates[ti].strftime("%Y-%m-%d"),
            "country": country, "category": cat, "surprise_bp": surprise,
            "description": f"SYNTHETIC {cat} event #{k + 1} ({surprise:+.1f}bp surprise)",
        })

    # --- price levels
    start_level = 1000.0 * (1 + np.arange(N) / N)
    close = start_level * np.exp(np.cumsum(ret, axis=0))
    prices = pd.DataFrame(close, index=dates, columns=codes)
    returns = pd.DataFrame(ret, index=dates, columns=codes)

    # --- institutional flows (USD mn, synthetic): foreign = trend-chasing + informed component
    z = ret / ret.std(axis=0, keepdims=True)
    scale = 150.0 * (1 + 2 * np.arange(N) / N)
    foreign = scale * (0.80 * u + 0.30 * np.vstack([np.zeros((1, N)), z[:-1]]))
    domestic = -0.5 * foreign + 0.2 * scale * rng.standard_normal((T, N))
    foreign_df = pd.DataFrame(foreign, index=dates, columns=codes)
    domestic_df = pd.DataFrame(domestic, index=dates, columns=codes)
    return {"returns": returns, "prices": prices, "foreign": foreign_df, "domestic": domestic_df,
            "events": events, "regime": pd.Series(state, index=dates)}
