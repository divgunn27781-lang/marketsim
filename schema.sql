-- Global Markets Database: schema
-- Conventions
--   * Every row that did not come from a cited source carries is_synthetic = 1.
--   * Reference/aggregate rows carry source, source_url and confidence ('high'|'medium'|'low').
--   * Dates are ISO-8601 text (YYYY-MM-DD).

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- exchanges
CREATE TABLE IF NOT EXISTS exchange (
    exchange_id     INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,      -- short key used as column name in models
    name            TEXT NOT NULL,
    operator        TEXT,
    country         TEXT NOT NULL,             -- ISO-3166 alpha-2
    region          TEXT NOT NULL,             -- Americas | EMEA | Asia-Pacific
    mic             TEXT,                      -- ISO-10383 market identifier code
    currency        TEXT NOT NULL,
    timezone        TEXT NOT NULL,             -- IANA tz name
    benchmark_index TEXT NOT NULL,
    is_emerging     INTEGER NOT NULL DEFAULT 0
);

-- Point-in-time statistics per exchange (market cap, listings, turnover ...)
CREATE TABLE IF NOT EXISTS exchange_stat (
    exchange_id INTEGER NOT NULL REFERENCES exchange(exchange_id),
    as_of       TEXT NOT NULL,
    metric      TEXT NOT NULL,                 -- e.g. domestic_market_cap
    value       REAL NOT NULL,
    unit        TEXT NOT NULL,                 -- e.g. USD tn
    source      TEXT NOT NULL,
    source_url  TEXT,
    confidence  TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    note        TEXT,
    PRIMARY KEY (exchange_id, as_of, metric, source)
);

-- Daily benchmark index levels and log returns
CREATE TABLE IF NOT EXISTS index_price (
    exchange_id  INTEGER NOT NULL REFERENCES exchange(exchange_id),
    date         TEXT NOT NULL,
    close        REAL NOT NULL,
    log_return   REAL,                         -- natural-log return, decimal (0.01 = 1%)
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (exchange_id, date)
);
CREATE INDEX IF NOT EXISTS ix_price_date ON index_price(date);

-- ---------------------------------------------------------------- investors
CREATE TABLE IF NOT EXISTS investor_class (
    class_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL                     -- foreign_institutional | domestic_institutional | alternatives | bank
);

-- Net buying (+) / selling (-) by investor class on an exchange
CREATE TABLE IF NOT EXISTS institutional_flow (
    exchange_id  INTEGER NOT NULL REFERENCES exchange(exchange_id),
    class_id     INTEGER NOT NULL REFERENCES investor_class(class_id),
    period_start TEXT NOT NULL,
    period_end   TEXT NOT NULL,
    frequency    TEXT NOT NULL CHECK (frequency IN ('daily','monthly','annual')),
    net_flow     REAL NOT NULL,
    unit         TEXT NOT NULL,                -- 'INR crore', 'USD mn' ...
    source       TEXT NOT NULL,
    source_url   TEXT,
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (exchange_id, class_id, period_start, period_end, frequency)
);

-- Hedge-fund / private-equity / private-markets / banking aggregates
-- (scope examples: global, country, hedge_fund, hedge_fund_strategy, private_equity,
--  private_markets, investment_banking)
CREATE TABLE IF NOT EXISTS market_aggregate (
    scope      TEXT NOT NULL,
    name       TEXT NOT NULL,                  -- e.g. 'Global', 'Equity Hedge', 'US'
    metric     TEXT NOT NULL,
    as_of      TEXT NOT NULL,
    value      REAL NOT NULL,
    unit       TEXT NOT NULL,
    is_forecast INTEGER NOT NULL DEFAULT 0,    -- 1 = projection published by the source
    source     TEXT NOT NULL,
    source_url TEXT,
    confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    note       TEXT,
    PRIMARY KEY (scope, name, metric, as_of, source)
);

-- Individual alternative-asset managers
CREATE TABLE IF NOT EXISTS alt_manager (
    manager            TEXT NOT NULL,
    segment            TEXT NOT NULL,          -- private_equity | hedge_fund
    as_of              TEXT NOT NULL,
    segment_aum_usd_bn REAL,
    firm_aum_usd_bn    REAL,
    source             TEXT NOT NULL,
    source_url         TEXT,
    confidence         TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    PRIMARY KEY (manager, segment, as_of)
);

-- Investment-bank league-table observations
CREATE TABLE IF NOT EXISTS ib_league (
    period     TEXT NOT NULL,                  -- '2026Q1', 'FY2025' ...
    bank       TEXT NOT NULL,
    metric     TEXT NOT NULL,                  -- advisory_deal_count | ma_volume_usd_tn | ib_fees_usd_bn
    value      REAL NOT NULL,
    rank       INTEGER,
    source     TEXT NOT NULL,
    source_url TEXT,
    confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    PRIMARY KEY (period, bank, metric, source)
);

-- ---------------------------------------------------------------- macro / policy
CREATE TABLE IF NOT EXISTS macro_series (
    country      TEXT NOT NULL,                -- ISO alpha-2 or 'GLOBAL'
    series       TEXT NOT NULL,                -- policy_rate | cpi_yoy | usd_index | brent ...
    date         TEXT NOT NULL,
    value        REAL NOT NULL,
    unit         TEXT,
    source       TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (country, series, date)
);

CREATE TABLE IF NOT EXISTS policy_event (
    event_id     INTEGER PRIMARY KEY,
    event_date   TEXT NOT NULL,
    country      TEXT NOT NULL,                -- ISO alpha-2
    category     TEXT NOT NULL,                -- monetary | fiscal | regulatory | trade | geopolitical
    description  TEXT NOT NULL,
    surprise_bp  REAL,                         -- signed surprise vs expectation, basis points (nullable)
    source       TEXT NOT NULL,
    source_url   TEXT,
    is_synthetic INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------- model outputs
CREATE TABLE IF NOT EXISTS model_run (
    run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT NOT NULL,
    data_through TEXT NOT NULL,
    uses_synthetic INTEGER NOT NULL,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS forecast_output (
    run_id      INTEGER NOT NULL REFERENCES model_run(run_id),
    exchange_id INTEGER NOT NULL REFERENCES exchange(exchange_id),
    horizon_days INTEGER NOT NULL,
    point_pct   REAL, lo80_pct REAL, hi80_pct REAL,
    oos_r2      REAL, hit_rate REAL, cw_tstat REAL, n_oos INTEGER,
    garch_alpha REAL, garch_beta REAL, ann_vol_forecast_pct REAL,
    PRIMARY KEY (run_id, exchange_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS risk_output (
    run_id      INTEGER NOT NULL REFERENCES model_run(run_id),
    exchange_id INTEGER NOT NULL REFERENCES exchange(exchange_id),
    metric      TEXT NOT NULL,
    value       REAL,
    PRIMARY KEY (run_id, exchange_id, metric)
);

CREATE TABLE IF NOT EXISTS spillover_output (
    run_id   INTEGER NOT NULL REFERENCES model_run(run_id),
    from_ex  INTEGER NOT NULL REFERENCES exchange(exchange_id),
    to_ex    INTEGER NOT NULL REFERENCES exchange(exchange_id),
    share    REAL NOT NULL,                    -- share of to_ex's forecast-error variance due to from_ex
    PRIMARY KEY (run_id, from_ex, to_ex)
);

CREATE TABLE IF NOT EXISTS event_result (
    run_id      INTEGER NOT NULL REFERENCES model_run(run_id),
    event_id    INTEGER NOT NULL REFERENCES policy_event(event_id),
    exchange_id INTEGER NOT NULL REFERENCES exchange(exchange_id),
    car_m1_p1   REAL, t_m1_p1 REAL,
    car_0_p5    REAL, t_0_p5  REAL,
    PRIMARY KEY (run_id, event_id, exchange_id)
);
