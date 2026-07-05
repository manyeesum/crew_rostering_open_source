# Methodology — the source framework

This file is the **canonical record of the trading methodology** this project
implements. It was distilled from six weekly-market-report videos of the
**Five Star Charts** YouTube channel (Cantonese; machine transcripts supplied
by the project owner during the founding session, 2026-07-05). The transcripts
themselves are not stored here — **this distillation is the source of truth**.
If code and this file disagree, this file wins; fix the code.

## The governing principle

> These indicators are **not for guessing the top**. They are an observation
> framework: **the more lights that come on, the more you shrink exposure; if
> nothing is lit, you don't shrink.** ("越多指標著燈就越縮")

Design consequences (do not violate these):
1. Output is a **panel of warning lights + a graded Caution Score**, never a
   binary buy/sell call.
2. Signals are evaluated **independently** and combined by weight; a single
   red light must never dominate the score on its own.
3. The presenter's stated purpose is *situation awareness* — participating in
   strength while staying ready to leave. Both failure modes matter: selling
   too early ("怕高就走") and overstaying ("音樂停咗都唔走").

## The five signals + overlay

### Signal #1 — 指鑽 / Breadth divergence (weight: highest)
Index makes new highs while participation narrows. Cited evidence:
- <60% of S&P stocks above their 50/200-day MA at index highs = topping
  (2000 top; also cited "56% above 50-day at all-time high" in 2026).
- **T2108** (% of stocks above 40-day MA): 63% at the high → 39% as top formed.
- NYSE **Advance-Decline line** making lower highs vs index higher highs
  (2021-11 → 2022-01 case; 2018-Q4 case).
- **4%+ movers**: count of stocks up 4%+ vs down 4%+ per day; "deep red" days
  clustering while the index still rises.
- Stocks up 25%+/month < stocks down 25%+/month while index rises.
- **Sector breadth**: more than half of sector ETFs below their 20-day MA with
  only defensives (XLU/XLP/energy) above = warning.
- **Narrow leadership**: ~20 stocks driving the index (2000 analog).
- Code: `breadth.py` (all functions), `barometer._light_breadth`.

### Signal #2 — 能減 / Momentum deceleration & over-extension
- Distance from **50-day MA in ATR units**: >5× = very extended; ~7× cited.
- Distance from **200-day MA in %**: 2000 leaders peaked ~90% above; AI-era
  leaders ~50–60% above ("F-pattern", historically only comparable to 2000).
- Index riding **above the upper weekly Bollinger band** for consecutive weeks
  ("~95% probability of mean reversion" framing).
- **RSI/momentum bearish divergence**: price higher-high, oscillator lower-high.
- Mean-reversion expectation: extended moves revert at least to the 50-day.
- Code: `indicators.distance_from_ma_atr/_pct`, `bollinger`,
  `bearish_divergence`, `barometer._light_momentum`.

### Signal #3 — 突破失敗 / Failed breakouts
- Individual momentum names break out of bases, stall within days, fall back
  into range and stop out (VRT early-2025 example).
- Personal trading **win-rate falling from ~70% to <40%** = the market, not
  you; response is to *shrink size*, not revenge-trade.
- Market-wide proxy: fraction of recent 20-day-high breakouts that closed back
  below the breakout level. Code: `breadth.failed_breakout_rate`,
  `barometer._light_failed_breakouts`.

### Signal #4 — 高波下跌日 / High-volatility down days & leader rollover
- Wide-range, heavy-volume down days clustering while the index still edges to
  marginal new highs (Dec-2024→Feb-2025 FOMC/DeepSeek/tariff sequence).
- Theme/momentum leaders (cited: PWR, GEV — data-center & power build-out) top
  and roll over *before* the index does; "rotation" narratives at that stage
  usually precede everything falling together.
- Code: `indicators.distribution_days`, `high_volatility_down_days`,
  `barometer._light_distribution`.

### Signal #5 — 市場對消息有反應 / News-reaction regime flip
- Strong tape **shrugs off bad news** (hot CPI/PPI ignored). The flip — market
  starts selling bad news, or starts pricing **rate hikes** — is a major
  change-of-character signal.
- Volatility tells: VIX/VXN **>30 = not a safe market**; and crucially
  **vol rising while the index rises** = large traders hedging into strength
  (buying protection while pushing the tape) — precedes sharp breaks.
- Code: `barometer._light_news_regime` (+ manual `news_reaction_negative`).

### Overlay — Macro / stagflation / cycle context
- **PPI leads CPI**: producer inflation gets passed to consumers (cited:
  PPI +1.1% m/m, ~6.5% y/y vs ~5.8% expected; core CPI 3.7–3.8%).
- **NFIB small-business optimism** below its ~98 long-run average (95.3 cited)
  = economy rolling over.
- **Stagflation** (high inflation + slowing growth + rising unemployment) →
  1970s analog: a decade of sideways equities; commodities/gold favored.
- **Rates/currency**: US & Japan 10Y rising; Japan/China selling Treasuries;
  bear steepener (long rates up while Fed cuts short rates) bad for equities,
  especially tech; USD pressure.
- **Cross-asset impossibility**: stocks at highs + oil +60% YTD + multi-decade
  high bond yields "cannot coexist" — one of them must break.
- **Leverage/sentiment**: margin debt > 2000/2007 records; leveraged-ETF and
  FOMO retail behavior (Samsung x2/x3 ETFs cited) = late-bubble psychology;
  mega-caps issuing bonds to fund AI capex (circular financing critique).
- **Housing tell**: homebuilders/construction (XHB) failing to confirm S&P
  highs = recession early-warning.
- **Seasonality**: sell-in-May (May→Sep weak); **midterm-election years**
  historically peak ~May/June and trough ~Sep/Oct.
- **Regime structure**: NYSE index vs a rising/falling long MA "zero line" —
  bull = holding above with bear counter-attacks failing; transition = price
  whipsawing the line; bear = holding below.
- Code: `barometer._light_macro`, `_regime_label` (+ manual overlay keys).

## Numbers the videos anchored (used as thresholds in `config.py`)

| Metric | Healthy | Warning | Source |
|---|---|---|---|
| % stocks above 50-day at index highs | >60% | <60%, worse <40% | videos #1, #4, #6 |
| T2108 (% above 40-day) | ~55%+ | 39% cited at top | video #2 |
| Distance from 50-day (ATR) | <4× | >5×, cited 7× | video #2 |
| Distance from 200-day (leaders) | — | 50–90% | videos #1, #4 |
| Distribution-day cluster | ≤2/25d | 4–5+/25d | classic + video #2 |
| VIX/VXN level | <20 | >30 | video #3 |
| Personal win-rate | ~70% | <40% | video #2 |
| NFIB | ~98+ | 95.3 cited | video #3 |
| PPI y/y | ~2% | 6.5% cited | videos #1, #3 |

## What is deliberately NOT implemented

- Price targets, head-and-shoulders projections, Elliott-style pattern calls —
  too subjective for a scored panel; keep them in human hands.
- The channel's stock/metal picks (gold above 7-month EMA, silver/platinum
  setups, GDX oversold plays) — out of scope: this is a *risk* monitor, not a
  buy-list generator. A future intermarket light may *reference* gold/oil/UST
  behavior as context only.
- IPO-supply timing (index funds selling to absorb mega-IPOs like the SpaceX
  listing discussion) — noted as a volatility catalyst; revisit if a reliable
  IPO-calendar source is added.
