# Research — what the trading community monitors for trend change

Compiled 2026-07-05 from a web-research sweep (trader forums/Reddit-adjacent
practice, StockCharts/Fidelity/Schwab education, McClellan Financial,
Quantifiable Edges, macro-research sites). Purpose: validate the
video-derived framework in `METHODOLOGY.md` against the broader community,
and identify additions. Findings drive the checks marked *(implemented)*.

## 1. Breadth — the community consensus core

The most-agreed-upon early-warning family, matching METHODOLOGY Signal #1:

- **Cumulative A-D line divergence** — index higher-high with A-D lower-high
  = narrowing leadership. The single most cited top-warning.
  *(implemented: A-D divergence check)*
- **McClellan Oscillator** (EMA19−EMA39 of net advancers) — breadth momentum;
  negative/diverging while the index presses highs = rally running out of
  participation. ±70 = overbought/oversold; a −50→+50 "thrust" marks major
  lows. *(implemented: universe-relative oscillator check)*
- **% stocks above 50/200-day MA** — trend participation. *(already core)*
- **Net new 52-week highs − lows** — a *split tape* (new lows expanding while
  the index is at highs — the Hindenburg-Omen ingredient) precedes damage.
  *(implemented: NH-NL check, gated on index-at-highs)*
- **Zweig Breadth Thrust** (10d EMA of advancers% from <40% to >61.5% within
  10 days) — a *bottom*/re-entry signal, not a top signal: ~16-20 triggers
  since 1950, strongly positive 6-12m forward returns (with occasional
  retests). → Roadmap: add as a green "re-entry" light so the monitor helps
  on the way back *in*, not just out.
- Caveat from the literature: **most divergences fail** — don't over-trigger
  on a single weak divergence; require confluence (our weighted-lights design
  already embodies this).

## 2. Trend/regime filters

- **200-day MA** — the community's master regime filter. S&P annualized
  ~+21% above vs ~−22% below (since 1950); Paul Tudor Jones' stated defense
  rule. Death cross (50<200) = slower confirmation. *(already core: regime
  label + golden-cross logic)*
- Nuance: *tests* of a rising 200-day are normal/healthy; the bear case is a
  **failed retest** below a flattening one. *(captured by TRANSITION regime)*

## 3. Volatility & options complex

- **VIX term structure**: VIX/VIX3M ratio — contango ~80% of the time;
  >0.95 = warning, >1.0 = backwardation/acute stress. Academic and
  practitioner work supports it as a regime gauge. *(implemented:
  auto-computed when ^VIX3M available)*
- **VIX level** >20 caution / >30 danger; **vol rising with price rising** =
  hedged distribution. *(already core)*
- **Put/call ratio** — contrarian at extremes; *low* readings (complacency)
  accompany tops. Works best in confluence with vol/breadth. *(implemented
  as manual overlay `put_call_complacent`; no reliable free feed)*

## 4. Fundamental / macro regime (slower, bigger turns)

- **Yield-curve un-inversion** — inversion warns, but recessions typically
  begin around *re-steepening* as the Fed cuts into weakness. *(implemented:
  manual `yield_curve_uninverting`)*
- **Sahm rule** — unemployment 3m-avg rising ≥0.5pt above its 12m low =
  recession onset confirmation (real-time, not predictive). *(implemented:
  manual `sahm_rule_triggered`)*
- **High-yield credit spreads** — "credit smells trouble first"; sustained
  >600bp = recessionary stress. Widening while equities hold up is a classic
  pre-top divergence. *(implemented: manual `credit_spreads_widening`;
  FRED `BAMLH0A0HYM2` on roadmap)*
- NFIB, PPI→CPI, margin debt, housing/homebuilders: community practice
  matches METHODOLOGY's overlay. *(already core)*

## 5. Risk-appetite ratio charts ("canaries")

Relative-strength ratios pros watch for character change:
- **XLY/XLP (discretionary/staples)** — the go-to risk-appetite read.
  *(implemented from existing sector data)*
- High-beta/low-vol (SPHB/SPLV), semis/S&P (SMH/SPY), copper/gold,
  silver/gold. → Roadmap: optional tickers in an intermarket light.

## 6. Risk-management arsenal (community doctrine → our playbook)

Consistent rules across trader communities; these operationalize what to *do*
at each barometer stance:

| Rule | Practice |
|---|---|
| Per-trade risk | Never >1-2% of capital per position |
| Vol-adjusted sizing | Size by ATR; cut risk 25-50% when ATR > its 6-month median |
| Drawdown protocol | −5% from equity high → cut risk 25%; −10-15% → cut 50%, A-setups only; >−15% → halt, review |
| Stops | Set at entry, mechanically honored; breakout entries invalidated back inside range (METHODOLOGY Signal #3) |
| Win-rate audit | Rolling win-rate 70%→<40% = market character changed → shrink size (video + community agree) |
| Automation beats willpower | Pre-committed rules/checklists, not in-the-moment judgment — exactly what this monitor is for |

Suggested mapping to Caution bands: RISK-ON = full size; CONSTRUCTIVE =
normal size, honor stops; CAUTION = halve new-position size, no leverage;
DEFENSIVE = no new longs, trim to core, hedge; RISK-OFF = capital
preservation. (Guidance text lives in `config.BANDS`.)

## 7. Gap analysis — status after this research round

| Community indicator | Status |
|---|---|
| A-D line, % above MAs, sector breadth | ✅ already core |
| McClellan Oscillator | ✅ added |
| Net new highs/lows (split tape) | ✅ added |
| VIX term structure (VIX/VIX3M) | ✅ added (auto w/ ^VIX3M) |
| XLY/XLP risk appetite | ✅ added |
| Put/call complacency | ✅ manual key |
| Yield-curve un-inversion, Sahm rule, credit spreads | ✅ manual keys (FRED auto = roadmap) |
| Zweig Breadth Thrust (re-entry signal) | ⏳ roadmap |
| SPHB/SPLV, SMH/SPY, copper/gold ratios | ⏳ roadmap (intermarket light) |
| AAII sentiment survey | covered by `euphoria` manual key |

### Sources
- StockCharts: [Charting Market Breadth Indicators](https://help.stockcharts.com/charts-and-tools/sharpcharts/sharpcharts-workbench/editing-sharpcharts/charting-market-breadth-indicators), [Three Breadth Signals That Help Confirm Market Trends](https://articles.stockcharts.com/article/three-breadth-signals-that-help-confirm-market-trends/), [McClellan Oscillator — ChartSchool](https://chartschool.stockcharts.com/table-of-contents/market-indicators/mcclellan-oscillator), [Below the 200-Day](https://articles.stockcharts.com/article/mindfulinvestor-2026-03-below-the-200-day-whats-next-for-the-s-p-500/), [Discretionary vs Staples](https://articles.stockcharts.com/article/consumer-discretionary-vs-staples-etfs-2025/)
- [Fidelity — Advance/Decline](https://www.fidelity.com/learning-center/trading-investing/advance-decline) · [Schwab — Breadth Check](https://www.schwab.com/learn/story/breadth-check-strength-and-weakness-trend-tracker)
- [McClellan Financial — Oscillator & Summation](https://www.mcoscillator.com/learning_center/kb/mcclellan_oscillator/the_mcclellan_oscillator_summation_index/) · [Zweig Breadth Thrust watch](https://www.mcoscillator.com/learning_center/weekly_chart/watching_for_a_zweig_breadth_thrust_signal/)
- [Quantifiable Edges — Zweig Thrust signals](https://quantifiableedges.com/a-look-at-zweig-thrust-signals/) · [OptionsTradingIQ — ZBT](https://optionstradingiq.com/zweig-breadth-thrust-signal/)
- [YCharts — Recession Indicators framework](https://get.ycharts.com/resources/blog/recession-indicators-2025-framework/) · [WhatIsARecession — indicator dashboard](https://whatisarecession.com/indicators) · [Lambda Finance — Yield-curve lead times](https://www.lambdafin.com/articles/yield-curve-inversion-recession-lead-time) · [RIA — Sahm Rule](https://realinvestmentadvice.com/resources/blog/the-sahm-rule-employment-and-recession-indicators/)
- [Volatility Box — VIX contango/backwardation](https://volatilitybox.com/research/vix-contango-backwardation/) · [Macrosynergy — VIX term structure as signal](https://macrosynergy.com/research/vix-term-structure-as-a-trading-signal/) · [MDPI — VIX futures as timing indicator](https://www.mdpi.com/1911-8074/12/3/113) · [FatTail — Put/Call guide](https://fattail.ai/put-call-ratio-guide/)
- [QuantifiedStrategies — 200-day MA backtest](https://www.quantifiedstrategies.com/200-day-moving-average-trading-strategy/) · [Investing.com — 200-day retests](https://www.investing.com/analysis/retest-of-the-200day-moving-average-isnt-bearishunless-it-fails-200661808) · [Motley Fool — death cross](https://www.fool.com/investing/2026/03/25/uh-oh-most-bearish-stock-market-signal-triggered/)
- [ITI — Dynamic position sizing](https://internationaltradinginstitute.com/blog/dynamic-position-sizing-and-risk-management-in-volatile-markets/) · [Medium/Coinmonks — Reddit trader risk rules](https://medium.com/coinmonks/extremely-profitable-day-trading-strategy-what-reddit-traders-actually-use-to-win-3c6ea37e43b6)
- [Britannica Money — Risk-on/risk-off](https://www.britannica.com/money/risk-on-vs-risk-off) · [Babypips — RORO meter](https://www.babypips.com/tools/risk-on-risk-off-meter)
