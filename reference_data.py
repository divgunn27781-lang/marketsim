"""Curated reference data (non-synthetic).

Every numeric value below was taken from a cited web source retrieved on 2026-11-11.
Exchange identity fields (name, MIC, currency, timezone, benchmark) are standard
reference facts; market-cap and flow figures are only loaded where a source gave them.
Exchanges with no sourced market cap simply have no exchange_stat row -- populate them
from the World Federation of Exchanges (WFE) monthly statistics via ingest_csv.py.

Confidence: 'high' = primary/regulatory or named research provider quoted directly,
'medium' = secondary article citing a primary provider, 'low' = weak/unattributed source.
"""

# code, name, operator, country, region, MIC, currency, timezone, benchmark, emerging
EXCHANGES = [
    ("NYSE",   "New York Stock Exchange",        "Intercontinental Exchange", "US", "Americas",     "XNYS", "USD", "America/New_York",    "NYSE Composite", 0),
    ("NASDAQ", "Nasdaq Stock Market",            "Nasdaq, Inc.",              "US", "Americas",     "XNAS", "USD", "America/New_York",    "Nasdaq Composite", 0),
    ("SSE",    "Shanghai Stock Exchange",        "SSE",                       "CN", "Asia-Pacific", "XSHG", "CNY", "Asia/Shanghai",       "SSE Composite", 1),
    ("SZSE",   "Shenzhen Stock Exchange",        "SZSE",                      "CN", "Asia-Pacific", "XSHE", "CNY", "Asia/Shanghai",       "SZSE Component", 1),
    ("JPX",    "Japan Exchange Group (Tokyo)",   "Japan Exchange Group",      "JP", "Asia-Pacific", "XJPX", "JPY", "Asia/Tokyo",          "Nikkei 225", 0),
    ("HKEX",   "Hong Kong Exchanges",            "HKEX",                      "HK", "Asia-Pacific", "XHKG", "HKD", "Asia/Hong_Kong",      "Hang Seng Index", 0),
    ("EURONEXT","Euronext",                      "Euronext N.V.",             "FR", "EMEA",         "XPAR", "EUR", "Europe/Paris",        "Euronext 100", 0),
    ("NSE",    "National Stock Exchange of India","NSE",                      "IN", "Asia-Pacific", "XNSE", "INR", "Asia/Kolkata",        "Nifty 50", 1),
    ("BSE",    "BSE Limited",                    "BSE",                       "IN", "Asia-Pacific", "XBOM", "INR", "Asia/Kolkata",        "S&P BSE Sensex", 1),
    ("TMX",    "Toronto Stock Exchange",         "TMX Group",                 "CA", "Americas",     "XTSE", "CAD", "America/Toronto",     "S&P/TSX Composite", 0),
    ("LSE",    "London Stock Exchange",          "LSEG",                      "GB", "EMEA",         "XLON", "GBP", "Europe/London",       "FTSE 100", 0),
    ("DB",     "Deutsche Boerse (Xetra)",        "Deutsche Boerse AG",        "DE", "EMEA",         "XETR", "EUR", "Europe/Berlin",       "DAX 40", 0),
    ("SIX",    "SIX Swiss Exchange",             "SIX Group",                 "CH", "EMEA",         "XSWX", "CHF", "Europe/Zurich",       "Swiss Market Index", 0),
    ("KRX",    "Korea Exchange",                 "KRX",                       "KR", "Asia-Pacific", "XKRX", "KRW", "Asia/Seoul",          "KOSPI", 0),
    ("TWSE",   "Taiwan Stock Exchange",          "TWSE",                      "TW", "Asia-Pacific", "XTAI", "TWD", "Asia/Taipei",         "TAIEX", 0),
    ("ASX",    "Australian Securities Exchange", "ASX Limited",               "AU", "Asia-Pacific", "XASX", "AUD", "Australia/Sydney",    "S&P/ASX 200", 0),
    ("B3",     "B3 - Brasil Bolsa Balcao",       "B3 S.A.",                   "BR", "Americas",     "BVMF", "BRL", "America/Sao_Paulo",   "Ibovespa", 1),
    ("TADAWUL","Saudi Exchange (Tadawul)",       "Saudi Tadawul Group",       "SA", "EMEA",         "XSAU", "SAR", "Asia/Riyadh",         "TASI", 1),
    ("JSE",    "Johannesburg Stock Exchange",    "JSE Limited",               "ZA", "EMEA",         "XJSE", "ZAR", "Africa/Johannesburg", "FTSE/JSE All Share", 1),
    ("SGX",    "Singapore Exchange",             "SGX Group",                 "SG", "Asia-Pacific", "XSES", "SGD", "Asia/Singapore",      "Straits Times Index", 0),
    ("BME",    "Bolsas y Mercados Espanoles",    "SIX Group (BME)",           "ES", "EMEA",         "XMAD", "EUR", "Europe/Madrid",       "IBEX 35", 0),
    ("IDX",    "Indonesia Stock Exchange",       "IDX",                       "ID", "Asia-Pacific", "XIDX", "IDR", "Asia/Jakarta",        "IDX Composite", 1),
    ("BMV",    "Bolsa Mexicana de Valores",      "Grupo BMV",                 "MX", "Americas",     "XMEX", "MXN", "America/Mexico_City", "S&P/BMV IPC", 1),
    ("NORDIC", "Nasdaq Stockholm (Nordic)",      "Nasdaq, Inc.",              "SE", "EMEA",         "XSTO", "SEK", "Europe/Stockholm",    "OMX Stockholm 30", 0),
    ("BURSA",  "Bursa Malaysia",                 "Bursa Malaysia Berhad",     "MY", "Asia-Pacific", "XKLS", "MYR", "Asia/Kuala_Lumpur",   "FTSE Bursa Malaysia KLCI", 1),
]

INVESTOR_CLASSES = [
    (1, "FII/FPI (foreign institutional)", "foreign_institutional"),
    (2, "DII (domestic institutional)",    "domestic_institutional"),
]

# ------------------------------------------------------------------ exchange stats
URL_EBC = "https://www.ebc.com/forex/top-10-stock-markets-in-the-world-every-investor-must-follow"
URL_DTZ = "https://daytradingz.com/largest-stock-exchanges-in-the-world/"
URL_JPX = "https://presentationbuilder.internationaltrucks.com/top-stock-exchanges-world"

# (exchange code, as_of, metric, value, unit, source, url, confidence, note)
EXCHANGE_STATS = [
    ("NASDAQ", "2026-03-31", "domestic_market_cap", 35.0, "USD tn", "WFE (Mar 2026 data) via EBC", URL_EBC, "medium",
     "Other web sources give very different NYSE/Nasdaq figures (operator-level vs domestic); WFE domestic basis used."),
    ("NYSE",   "2026-03-31", "domestic_market_cap", 31.0, "USD tn", "WFE (Mar 2026 data) via EBC", URL_EBC, "medium",
     "Same caveat as Nasdaq; some sites quote ~$20tn or ~$28tn."),
    ("SSE",    "2026-04-30", "domestic_market_cap", 10.21, "USD tn", "Wikipedia list of major exchanges (Apr/May 2026) via daytradingz", URL_DTZ, "medium", None),
    ("HKEX",   "2026-03-31", "domestic_market_cap", 5.9, "USD tn", "WFE (Mar 2026 data) via EBC", URL_EBC, "medium", None),
    ("BSE",    "2026-03-31", "domestic_market_cap", 4.33, "USD tn", "WFE (Mar 2026 data) via EBC", URL_EBC, "medium",
     "Source says NSE is slightly above this figure."),
    ("JPX",    "2026-04-30", "domestic_market_cap", 6.5, "USD tn", "Aggregator page (unattributed)", URL_JPX, "low",
     "Approximate; verify against WFE before use."),
]

# ------------------------------------------------------------------ India FII / DII
URL_TAPE = "https://tapetide.com/insight/reports/fii-dii-flows/"
URL_SEBI = "https://ianslive.in/rs-85-lakh-crore-dii-inflows-dwarf-fpi-outflows-in-fy26-sebi--20260807103616"

# (exchange, class_id, start, end, frequency, net_flow, unit, source, url)
INDIA_FLOWS = [
    ("NSE", 1, "2026-01-01", "2026-01-31", "monthly",  -41435.22, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-01"),
    ("NSE", 1, "2026-02-01", "2026-02-28", "monthly",   -6640.76, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-02"),
    ("NSE", 2, "2026-02-01", "2026-02-28", "monthly",   38423.11, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-02"),
    ("NSE", 1, "2026-03-01", "2026-03-31", "monthly", -122540.41, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-03"),
    ("NSE", 2, "2026-03-01", "2026-03-31", "monthly",  142960.37, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-03"),
    ("NSE", 1, "2026-04-01", "2026-04-30", "monthly",  -70135.46, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-04"),
    ("NSE", 2, "2026-04-01", "2026-04-30", "monthly",   51063.87, "INR crore", "Tapetide (NSE/BSE provisional data)", URL_TAPE + "2026-04"),
    # SEBI annual report, FY26 (1 Apr 2025 - 31 Mar 2026): Rs 8.5 lakh crore = 850,000 crore; Rs 1.8 lakh crore = 180,000 crore
    ("NSE", 2, "2025-04-01", "2026-03-31", "annual",   850000.0, "INR crore", "SEBI annual report via IANS", URL_SEBI),
    ("NSE", 1, "2025-04-01", "2026-03-31", "annual",  -180000.0, "INR crore", "SEBI annual report via IANS (FPI equity)", URL_SEBI),
]

# ------------------------------------------------------------------ aggregates
URL_HFR_Q2 = "https://www.hfr.com/?p=45906"
URL_HFR_Q3 = "https://www.opalesque.com/fullarticle/716872/Hedge_fund_assets_hold_at_record_trillion687.html"
URL_HFR_Q1 = "https://www.hfr.com/media/market-commentary/investor-inflows-drive-global-hedge-fund-industry-capital-to-new-record-as-geopolitical-risks-surge/"
URL_HFR_Q4 = "https://alpha-maven.com/story/hedge-fund/hfr-says-hedge-fund-industry-capital-hit-another-record-hedgeconet"
URL_HFR_NET = "https://www.hedgeweek.com/hedge-fund-assets-surge-by-record-409bn-to-5-6tn-in-q2/"
URL_WALNUT_PE = "https://walnutinvest.com/stats/private-equity-statistics"
URL_KPMG = "https://kpmg.com/se/en/industries/private-equity/pulse-of-private-equity.html"
URL_PITCH = "https://www.crowdfundinsider.com/?p=281180"
URL_LSEG = "https://www.investmentexecutive.com/news/markets/strong-markets-boost-bankers-fortunes/"
URL_BAIN = "https://www.bain.com/insights/outlook-gaining-traction-global-private-equity-report-2026"

# (scope, name, metric, as_of, value, unit, is_forecast, source, url, confidence, note)
MARKET_AGGREGATES = [
    # -- global / country equity market capitalisation
    ("global", "World", "equity_market_cap", "2026-01-01", 150.0, "USD tn", 0, "WFE via aggregator", "https://presentationbuilder.internationaltrucks.com/top-stock-exchanges-world-2", "low", "'Surged past $150tn'; lower bound."),
    ("country", "US", "equity_market_cap", "2026-04-30", 75.0, "USD tn", 0, "Visual Capitalist via bursa.ro", "https://www.bursa.ro/us-china-japan-the-worlds-largest-stock-markets-48181952", "medium", "'Over $75tn'; lower bound."),
    ("country", "CN", "equity_market_cap", "2026-04-30", 14.84, "USD tn", 0, "Visual Capitalist via bursa.ro", "https://www.bursa.ro/us-china-japan-the-worlds-largest-stock-markets-48181952", "medium", None),
    ("country", "CA", "equity_market_cap", "2026-04-30", 4.49, "USD tn", 0, "Visual Capitalist via bursa.ro", "https://www.bursa.ro/us-china-japan-the-worlds-largest-stock-markets-48181952", "medium", None),
    # -- hedge funds (HFR)
    ("hedge_fund", "Global", "industry_capital", "2025-09-30", 4980.0, "USD bn", 0, "HFR Global Hedge Fund Industry Report", URL_HFR_Q4, "high", None),
    ("hedge_fund", "Global", "industry_capital", "2025-12-31", 5160.0, "USD bn", 0, "HFR Global Hedge Fund Industry Report", URL_HFR_Q4, "high", None),
    ("hedge_fund", "Global", "industry_capital", "2026-03-31", 5220.0, "USD bn", 0, "HFR Global Hedge Fund Industry Report", URL_HFR_Q1, "high", None),
    ("hedge_fund", "Global", "industry_capital", "2026-06-30", 5600.0, "USD bn", 0, "HFR Global Hedge Fund Industry Report", URL_HFR_Q2, "high", "Record +$409.3bn quarterly increase."),
    ("hedge_fund", "Global", "industry_capital", "2026-09-30", 5640.0, "USD bn", 0, "HFR Global Hedge Fund Industry Report", URL_HFR_Q3, "high", "16th consecutive quarterly increase."),
    ("hedge_fund", "Global", "net_investor_inflow_quarter", "2026-06-30", 45.2, "USD bn", 0, "HFR via Hedgeweek", URL_HFR_NET, "high", "Performance contributed ~$364bn of the Q2 increase."),
    ("hedge_fund", "Global", "net_investor_inflow_ytd", "2026-09-30", 124.1, "USD bn", 0, "HFR 3Q26 via Opalesque", URL_HFR_Q3, "high", "Jan-Sep 2026."),
    ("hedge_fund", "Global", "hfri_fw_composite_return_h1", "2026-06-30", 7.5, "pct", 0, "HFR via Hedgeweek", URL_HFR_NET, "high", "Strongest first half since 2021."),
    ("hedge_fund_strategy", "Equity Hedge", "industry_capital", "2026-06-30", 1760.0, "USD bn", 0, "HFR", URL_HFR_Q2, "high", None),
    ("hedge_fund_strategy", "Macro", "industry_capital", "2026-06-30", 857.5, "USD bn", 0, "HFR via Hedgeweek", URL_HFR_NET, "high", None),
    # -- private equity / private markets
    ("private_equity", "Global", "aum", "2024-12-31", 8600.0, "USD bn", 0, "Preqin via Walnut Invest", URL_WALNUT_PE, "medium", None),
    ("private_equity", "Global", "aum", "2030-12-31", 11800.0, "USD bn", 1, "Preqin forecast via Walnut Invest", URL_WALNUT_PE, "medium", "Projection."),
    ("private_equity", "Global", "dry_powder_all_pe", "2026-01-01", 3700.0, "USD bn", 0, "Preqin via Walnut Invest", URL_WALNUT_PE, "medium", "Broader scope than KPMG/PitchBook figures below."),
    ("private_equity", "Global", "dry_powder_pe_kpmg", "2025-12-31", 1700.0, "USD bn", 0, "KPMG Pulse of Private Equity", URL_KPMG, "medium", "Different scope from Preqin; do not mix."),
    ("private_equity", "Global", "exit_value", "2025-12-31", 1300.0, "USD bn", 0, "KPMG Pulse of Private Equity", URL_KPMG, "medium", "Second-highest year of the decade."),
    ("private_equity", "Global", "announced_deal_value_q4", "2025-12-31", 2100.0, "USD bn", 0, "KPMG Pulse of Private Equity", URL_KPMG, "medium", "19,093 transactions in Q4 2025."),
    ("private_equity", "Global", "fundraising_t12m", "2026-03-31", 385.0, "USD bn", 0, "PitchBook via Crowdfund Insider", URL_PITCH, "medium", "Down 29% year on year."),
    ("private_equity", "Healthcare buyouts", "buyout_deal_value", "2025-12-31", 190.0, "USD bn", 0, "Bain Global PE Report 2026 via Walnut Invest", URL_WALNUT_PE, "medium", "Record."),
    ("private_markets", "Global", "aum", "2026-03-31", 20000.0, "USD bn", 0, "PitchBook via Crowdfund Insider", URL_PITCH, "medium", "'Around $20tn'."),
    ("private_markets", "Global", "aum", "2030-12-31", 26700.0, "USD bn", 1, "PitchBook forecast via Crowdfund Insider", URL_PITCH, "medium", "Projection, 5.7% CAGR."),
    # -- investment banking (LSEG)
    ("investment_banking", "Global", "fees_9m", "2026-09-30", 117.0, "USD bn", 0, "LSEG Data & Analytics via Investment Executive", URL_LSEG, "medium", "+12% on the same period of 2025."),
    ("investment_banking", "Global", "fees_9m_yoy_equity_underwriting", "2026-09-30", 37.0, "pct", 0, "LSEG via Investment Executive", URL_LSEG, "medium", None),
    ("investment_banking", "Global", "fees_9m_yoy_ma", "2026-09-30", 15.0, "pct", 0, "LSEG via Investment Executive", URL_LSEG, "medium", None),
    ("investment_banking", "Global", "fees_9m_yoy_debt_underwriting", "2026-09-30", 6.0, "pct", 0, "LSEG via Investment Executive", URL_LSEG, "medium", None),
    ("investment_banking", "Global", "fees_q3_qoq", "2026-09-30", -19.0, "pct", 0, "LSEG via Investment Executive", URL_LSEG, "medium", None),
    ("investment_banking", "Goldman Sachs", "ib_fees_q1", "2026-03-31", 2.84, "USD bn", 0, "Finimize (company results)", "https://finimize.com/content/goldman-hit-1-trillion-in-ma-in-half-a-year", "medium", "+48% year on year."),
    ("investment_banking", "Evercore", "advisory_fees_fy", "2025-12-31", 3.3, "USD bn", 0, "DealRoom (company results)", "https://dealroom.net/blog/%20best-investment-banks-to-work-for", "medium", "+34% year on year."),
]

# (manager, segment, as_of, segment_aum_bn, firm_aum_bn, source, url, confidence)
URL_PE_FIRMS = "https://investingintheweb.com/?p=43491"
ALT_MANAGERS = [
    ("Blackstone",     "private_equity", "2026-06-30", 454.2, None,  "Investing in the Web (company Q2-26 results)", URL_PE_FIRMS, "medium"),
    ("KKR",            "private_equity", "2026-06-30", 255.0, 796.0, "Investing in the Web (company Q2-26 results)", URL_PE_FIRMS, "medium"),
    ("Thoma Bravo",    "private_equity", "2026-06-30", 170.0, None,  "Investing in the Web", URL_PE_FIRMS, "medium"),
    ("Brookfield",     "private_equity", "2026-06-30", 166.0, 1300.0, "Investing in the Web (company Q2-26 supplemental)", URL_PE_FIRMS, "medium"),
    ("Ardian",         "private_equity", "2026-06-30", 137.0, 200.0, "Investing in the Web", URL_PE_FIRMS, "medium"),
    ("General Atlantic","private_equity","2026-06-30", None,  130.0, "Investing in the Web", URL_PE_FIRMS, "medium"),
    ("Bridgewater",    "hedge_fund",     "2025-06-30", 78.0,  None,  "Pensions & Investments via Walnut Invest (net HF assets)", "https://walnutinvest.com/stats/hedge-fund-statistics", "medium"),
    ("Millennium",     "hedge_fund",     "2025-06-30", 77.5,  None,  "Pensions & Investments via Walnut Invest (net HF assets)", "https://walnutinvest.com/stats/hedge-fund-statistics", "medium"),
    ("Elliott",        "hedge_fund",     "2025-06-30", 76.1,  None,  "Pensions & Investments via Walnut Invest (net HF assets)", "https://walnutinvest.com/stats/hedge-fund-statistics", "medium"),
]

# (period, bank, metric, value, rank, source, url, confidence)
URL_DAK1 = "https://www.dakota.com/reports-blog/1q-2026-investment-banking-league-table"
URL_DAK2 = "https://www.dakota.com/reports-blog/investment-banks-league-table-2q26?hs_amp=true"
IB_LEAGUE = [
    ("2025Q4", "Goldman Sachs", "advisory_deal_count", 50, None, "Dakota Marketplace", URL_DAK1, "medium"),
    ("2026Q1", "Goldman Sachs", "advisory_deal_count", 73, 1, "Dakota Marketplace", URL_DAK1, "medium"),
    ("2026Q2", "Goldman Sachs", "advisory_deal_count", 64, 1, "Dakota Marketplace", URL_DAK2, "medium"),
    ("FY2025", "Goldman Sachs", "ma_volume_usd_tn", 1.48, 1, "Reuters (LSEG)", "https://www.nst.com.my/amp/business/corporate/2026/01/1352029/goldman-sachs-tops-global-ma-rankings-us148tri-deals", "high"),
]

# ------------------------------------------------------------------ real policy / geopolitical events
# (date, country, category, description, surprise_bp, source, url)
REAL_POLICY_EVENTS = [
    ("2025-04-02", "US", "trade", "US 'Liberation Day' tariff announcement; global market turmoil", None,
     "Bain Global Private Equity Report 2026", URL_BAIN),
    ("2026-04-01", "IN", "geopolitical", "Middle East ceasefire announcement; EM recovery but continued FPI selling in India", None,
     "Multibagg market pulse", "https://www.multibagg.ai/market-pulse/articles/fii-selling-dii-buying-spike-cmoug0hs1001bpl0j3sc0pqfv"),
]
