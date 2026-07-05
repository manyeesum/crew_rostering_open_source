"""
Configuration: the tradeable universe, default weights and the scoring
thresholds. Everything a user is likely to tune lives here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------
# Benchmark index proxy (used for trend / extension / distribution-day checks).
BENCHMARK = "SPY"

# The 11 SPDR sector ETFs -- used for sector breadth and defensive rotation.
SECTOR_ETFS = ["XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLU", "XLP", "XLV", "XLRE"]
DEFENSIVE_SECTORS = ["XLU", "XLP", "XLV"]
CYCLICAL_SECTORS = ["XLK", "XLY", "XLF", "XLI"]

# A diversified large-cap universe used to compute participation breadth.
# For production-grade breadth, replace this with the full index membership
# (e.g. all S&P 500 tickers) -- see README. This curated ~40-name list keeps the
# demo light while still exercising every breadth metric.
BREADTH_UNIVERSE = [
    # mega-cap tech / "the generals"
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "AMD", "NFLX",
    # financials
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    # health
    "UNH", "JNJ", "LLY", "PFE", "MRK",
    # industrials / energy / materials
    "CAT", "GE", "BA", "HON", "XOM", "CVX", "FCX", "NUE",
    # staples / utilities / defensives
    "PG", "KO", "PEP", "WMT", "COST", "NEE", "DUK", "SO",
    # discretionary / other
    "HD", "MCD", "NKE", "DIS",
]

VIX = "^VIX"
VIX3M = "^VIX3M"   # 3-month implied vol; VIX/VIX3M > ~1.0 = backwardation (stress)

# ---------------------------------------------------------------------------
# Light weights  (the six "warning lights"; must sum to ~1.0)
# Breadth is weighted highest -- it is the presenter's Signal #1 and his most
# emphasised tell.
# ---------------------------------------------------------------------------
LIGHT_WEIGHTS = {
    "breadth_divergence": 0.28,     # Signal #1  指鑽
    "momentum_extension": 0.24,     # Signal #2  能減 / over-extension
    "failed_breakouts": 0.12,       # Signal #3  突破失敗
    "distribution": 0.20,           # Signal #4  高波下跌日
    "news_regime": 0.08,            # Signal #5  市場對消息有反應
    "macro_overlay": 0.08,          # inflation / rates / oil / USD context
}

# ---------------------------------------------------------------------------
# Thresholds. Each (lo, hi) pair feeds a ramp: intensity 0 at the "healthy"
# end, 1 at the "warning" end. Tuned to the figures cited in the videos.
# ---------------------------------------------------------------------------
TH = {
    # breadth
    "pct_above_50_hi": 60.0, "pct_above_50_lo": 40.0,     # <60% while index high = topping
    "pct_above_200_hi": 60.0, "pct_above_200_lo": 40.0,   # same read on the 200-day
    "t2108_hi": 55.0, "t2108_lo": 35.0,                   # % above 40-day (T2108); 39% cited
    "sectors_above20_hi": 60.0, "sectors_above20_lo": 30.0,
    "defensive_rot_lo": 0.0, "defensive_rot_hi": 3.0,     # 21d % gain of def/cyc ratio
    "thrust_net_lo": 0.0, "thrust_net_hi": -8.0,          # trailing (up-down) 4% movers; negative = bad
    "nhnl_lo": 0.0, "nhnl_hi": -5.0,                      # net new 52wk highs-lows while index high
    "mcclellan_lo": 0.0, "mcclellan_hi": -20.0,           # oscillator negative while index high
    "risk_appetite_lo": 0.0, "risk_appetite_hi": -4.0,    # XLY/XLP 21d %chg; falling = risk-off
    # momentum / extension
    "dist50_atr_lo": 4.0, "dist50_atr_hi": 7.0,           # >5x stretched, ~7x now
    "dist200_pct_lo": 20.0, "dist200_pct_hi": 50.0,       # 2000=90%, AI ~50-60%
    "pctb_lo": 0.95, "pctb_hi": 1.10,                     # above upper Bollinger band
    # failed breakouts
    "failbo_lo": 0.30, "failbo_hi": 0.70,
    "winrate_hi": 0.55, "winrate_lo": 0.40,               # personal win-rate 70->40 cited
    # distribution
    "dist_days_lo": 3.0, "dist_days_hi": 6.0,
    "hivol_down_lo": 2.0, "hivol_down_hi": 5.0,
    "updown_vol_hi": 1.0, "updown_vol_lo": 0.6,           # <1 = distribution
    # news regime
    "vix_spike_lo": 0.0, "vix_spike_hi": 20.0,            # 5d % rise in VIX while mkt down
    "vix_ts_lo": 0.90, "vix_ts_hi": 1.00,                 # VIX/VIX3M; >0.95 warning, >1 backwardation
}

# ---------------------------------------------------------------------------
# Caution-score bands -> exposure guidance. Higher caution = trim more, exactly
# the presenter's rule "the more lights on, the more you shrink".
# ---------------------------------------------------------------------------
BANDS = [
    (0, 20, "RISK-ON", "Broad, healthy uptrend. Full participation warranted."),
    (20, 40, "CONSTRUCTIVE", "Trend intact but watch the amber lights; keep stops."),
    (40, 60, "CAUTION", "Internals deteriorating. Trim winners, cut leverage, tighten stops."),
    (60, 80, "DEFENSIVE", "Multiple tops-signals lit. Raise cash materially, hedge."),
    (80, 100, "RISK-OFF", "Weight of evidence says exit. Capital preservation mode."),
]
