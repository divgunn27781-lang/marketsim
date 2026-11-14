# Global Markets Database and Risk/Forecasting Model

A working prototype: a SQLite database covering 25 major exchanges, institutional and alternative
investor activity, and policy events, plus four models on top of it (forecasting, risk, policy-event
analysis, contagion). Built 2026-11-11.

## Read this first: what is real and what is not

| Part | Status |
|---|---|
| Exchange identities (name, MIC, currency, timezone, benchmark) | Standard reference facts |
| Market caps for 6 of 25 exchanges | Sourced (WFE via secondary articles); 19 are **empty**, fill from WFE |
| India FII/DII flows (Jan-Apr 2026 monthly, FY26 annual) | Sourced (Tapetide, SEBI via IANS) |
| Hedge fund, private equity, investment banking aggregates and manager AUM | Sourced (HFR, Preqin, KPMG, PitchBook, LSEG, Bain, Dakota), each with URL and confidence |
| **Daily index prices, daily flows, 40 policy events** | **SYNTHETIC** (`is_synthetic = 1`). Generated to test the pipeline |

The synthetic data has structure injected on purpose (volatility regimes, a flow-to-return link, a known
policy response). Model results on it prove the code works, **not** that markets behave this way. No real
price history was available in the build environment (no market-data feed, no network for packages).

## Quick start

```bash
python3 build_db.py                  # builds global_markets.db (add --no-synthetic for reference data only)
python3 run_pipeline.py              # runs all models, writes outputs/ and model tables in the DB
python3 tests/test_models.py         # 7 correctness tests
```

Requires Python 3 with numpy, pandas, scipy (scikit-learn and matplotlib are not used by the models).

## Loading real data (one command path)

```bash
python3 build_db.py --no-synthetic     # reference data only, no synthetic rows
python3 fetch_real_data.py             # downloads daily closes for all 25 benchmarks (needs internet) and loads them
python3 run_pipeline.py --include-real-events
python3 tools/build_html.py            # HTML report; the synthetic-data banner disappears automatically
```

`fetch_real_data.py` uses Yahoo Finance's unofficial chart endpoint (no key; research use only) and skips any
market that fails, listing it at the end. On GitHub, run the **Run on real market data** workflow (manual button, and
weekdays at 07:00 IST). Holidays are treated as zero-return days inside each market's own history.
Not included: daily FII/DII flows (load with `ingest_csv.py flows` from NSDL, KRX, TWSE, JPX) and policy-surprise sizes.
Without flows the forecast model runs on prices only; without surprises only event returns are measured, not sensitivity.

## Attaching other real data

```bash
python3 ingest_csv.py prices --db global_markets.db --exchange NSE --csv nifty.csv      # date,close
python3 ingest_csv.py flows  --db global_markets.db --exchange NSE --class 1 --csv fii.csv --unit "INR crore" --source NSDL
python3 ingest_csv.py events --db global_markets.db --csv events.csv --source RBI        # event_date,country,category,description[,surprise_bp]
python3 run_pipeline.py --include-real-events
```

Loading real prices for an exchange deletes that exchange's synthetic rows first, so real and synthetic
series are never mixed. Priority data to load: daily benchmark closes for all 25 exchanges, daily FPI/DII
flows (NSDL for India, KRX/TWSE/JPX investor-type statistics elsewhere), central-bank decisions with
market-implied surprise (e.g. fed funds futures move), WFE monthly market statistics.

## Layout

```
schema.sql          tables: exchange, exchange_stat, index_price, investor_class, institutional_flow,
                    market_aggregate, alt_manager, ib_league, macro_series, policy_event, model outputs
reference_data.py   all sourced figures, each with source, URL and confidence
synthetic.py        synthetic data generator (documents exactly what is injected)
build_db.py         creates and loads the database
ingest_csv.py       loader for real prices, flows and events
gm_model/
  forecast.py       GARCH(1,1) + walk-forward ridge, Clark-West test
  risk.py           VaR/ES (historical, normal, Student-t, GARCH-FHS), Kupiec/Christoffersen backtests,
                    tail-beta stress scenarios, composite 0-100 risk score
  policy.py         market-model event study, CAR by policy category, surprise-to-return regression
  contagion.py      Diebold-Yilmaz spillover index, absorption ratio, correlation regimes, centrality
run_pipeline.py     orchestrates everything, writes outputs/report.md and CSVs
tests/              correctness tests
outputs/            latest run: report.md, forecasts.csv, risk_metrics.csv, spillover_*.csv, event_study.csv ...
```

## What the models do

- **Forecasting.** Predicts the 5-day-ahead return from own momentum, volatility, foreign and domestic flows
  and a global-return factor. Expanding window, refit every 21 days, training rows only where the target was
  already known (a test proves future data cannot change past predictions). Scored against a
  historical-mean benchmark with out-of-sample R^2, hit rate and the Clark-West test.
  GARCH gives volatility and the 80% interval.
- **Risk.** One-day VaR and expected shortfall by four methods; the 99% GARCH-filtered VaR is backtested
  out of sample. Stress scenarios shock the global factor by 3, 5 and 8 sigma and transmit it with betas
  estimated on global down-days only.
- **Policy.** Event study around each policy event with a benchmark that excludes the event country, then
  the sensitivity of the announcement-window return to the surprise size, by policy category.
- **Contagion.** Generalised variance-decomposition spillover index (total, to, from, net), rolling
  version, correlation in calm vs stressed regimes, absorption ratio, network centrality.

## Known limitations

- **Net transmitter/receiver ranks are not causal.** The spillover method uses same-day covariance, so
  high-beta, high-variance markets rank as net transmitters. With real data, correct for time-zone
  asynchrony (lag Asia-Pacific returns or use synchronised snapshots) before interpreting direction.
- Hedge fund, private equity and investment banking figures are context only; they are quarterly or annual
  aggregates and do not yet feed a model. Linking them to markets needs a longer series (HFR/Preqin
  history, LSEG fee data).
- Sources conflict on some figures (e.g. NYSE market cap quoted at roughly $20tn, $28tn and $31tn by
  different sites depending on operator versus domestic basis). The database records which one was used.
- Several sourced values come from secondary articles and carry `medium` or `low` confidence; verify
  against the primary publisher before relying on them.
- This is an analytical prototype, not investment advice or a validated production risk system.
