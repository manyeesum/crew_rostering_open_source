# Market Barometer 🌡️

A composite, multi-signal **market-timing situation-awareness panel** — a monitor
that tells you *when the internals of the market are deteriorating* so you can
decide how much to be invested vs. how much to move to cash.

It is a code implementation of the technical-analysis methodology taught on the
**Five Star Charts** weekly-market-report videos. The guiding principle is the
presenter's own, and it shapes the whole design:

> These indicators are **not** for guessing the top. They are an *observation
> framework*: **the more lights that come on, the more you shrink exposure; if
> nothing is lit, you don't shrink.** The goal is *situation awareness* — to
> stay in a strong bull market while being ready to leave, avoiding both
> "selling too early out of fear of heights" and "not leaving when the music
> stops."

So the tool does **not** emit a naked "BUY/SELL". It emits a **Caution Score
(0–100)**, a count of **how many warning lights are lit**, and a suggested
**exposure stance**.

> ⚠️ **Educational tool only. Not investment advice.** Markets can stay
> irrational; every signal here can be early or wrong. Do your own research and
> consult a licensed professional before making decisions.

**Project documentation:**
- [`GUIDE.md`](GUIDE.md) — **start here if you're not a programmer**: step-by-step setup, the exact StockCharts download list, daily/monthly routine, troubleshooting
- [`METHODOLOGY.md`](METHODOLOGY.md) — the distilled source framework (canonical; code serves it)
- [`RESEARCH.md`](RESEARCH.md) — community/literature validation with sources; risk-management playbook
- [`GOVERNANCE.md`](GOVERNANCE.md) — architecture rules, data contracts, verification gate, roadmap, handoff guide
- `tests/` — the behavioral contract; run `python -m market_barometer.tests.test_barometer`

---

## The six warning lights

Each "light" corresponds to one of the presenter's signals. A light is built
from several checks; each check maps a raw indicator to a 0–1 *warning
intensity* (0 = all-clear, 1 = full warning). Lights combine (weighted) into the
Caution Score.

| Light | Presenter's signal | What it looks at | Source video |
|------|--------------------|------------------|--------------|
| **1. Breadth / Participation** | 指鑽 (breadth divergence) | % stocks above 20/50-day MA, **T2108** (% above 40-day), NYSE A-D line divergence, 4%+ up/down "thrust" days, up/down volume, % sectors above 20-day MA, defensive-vs-cyclical rotation | #1, #2, #4, #5 |
| **2. Momentum / Over-extension** | 能減 (deceleration & stretch) | Distance from 50-day in **ATR units** (>5× stretched, ~7× cited), distance from 200-day in % (2000 peak ~90%, AI ~50-60%), Bollinger %B (riding above upper band), **RSI bearish divergence**, MACD fade on new highs | #1, #2, #3 |
| **3. Failed Breakouts** | 突破失敗 | % of recent 20-day-high breakouts that rolled back into range; optional personal **win-rate** (70% → <40% = danger) | #2 |
| **4. Distribution / High-Vol Down Days** | 高波下跌日 | IBD-style distribution-day count (down on higher volume), wide-range heavy-volume down days | #2, #3 |
| **5. Volatility & News Regime** | 市場對消息有反應 | VIX/VXN spike on weakness, **absolute vol level (>30 = danger)**, **vol rising *into* strength (hedging)**, market starting to *sell* bad news / price rate hikes | #2, #3, #4 |
| **6. Macro / Stagflation Overlay** | inflation · rates · growth | NFIB small-biz optimism (95.3 < 98 avg), **PPI y/y** (leads CPI), stagflation regime, 10Y-yield rising / Treasury dumping, **bear steepener**, margin-debt extreme, euphoria/FOMO, homebuilder (XHB) divergence, sell-in-May / midterm-election **seasonality** | #3, #4, #5, #6 |

Default light weights (in `config.py`) put the most weight on **breadth** and
**over-extension**, the presenter's two most-emphasised tells.

### Caution Score → stance

| Score | Stance | Action |
|------:|--------|--------|
| 0–20 | **RISK-ON** | Broad healthy uptrend — full participation |
| 20–40 | **CONSTRUCTIVE** | Trend intact, watch the amber lights, keep stops |
| 40–60 | **CAUTION** | Internals deteriorating — trim winners, cut leverage |
| 60–80 | **DEFENSIVE** | Multiple tops-signals lit — raise cash materially, hedge |
| 80–100 | **RISK-OFF** | Weight of evidence says exit — capital preservation |

There is also a **regime label** (BULL / BEAR / TRANSITION / late-cycle chop)
derived from price vs. a rising/falling 200-day "zero line" — the bull/bear
structure idea from video #3.

---

## Install & run

```bash
cd market_barometer
pip install -r requirements.txt
```

**Prove the engine with no network** (this is what the repo ships tested):

```bash
python -m market_barometer.run --source synthetic --scenario topping
python -m market_barometer.run --source synthetic --scenario healthy
```

**Run it live on your own machine** (needs Yahoo Finance access):

```bash
python -m market_barometer.run --source yfinance --period 2y
```

**Add the macro / sentiment overlays** you read off FRED / your broker / the news
(these can't all be pulled automatically):

```bash
python -m market_barometer.run --source yfinance \
  --macro nfib=95.3,ppi_yoy=6.5,stagflation=1,margin_debt_extreme=1,euphoria=1,\
yield_10y_rising=1,yield_curve_steepening=1,homebuilders_diverging=1,win_rate=0.42
```

### Sample output (synthetic topping tape)

```
  CAUTION SCORE  [##################----------------------] 46/100
  STANCE:  CAUTION  —  Internals deteriorating. Trim winners, cut leverage, tighten stops.
  Lights lit: 5/6

  🟡 Breadth / Participation      AMBER   ! % above 50-day 34% · ! T2108 39% · ! A-D divergence
  🟢 Momentum / Over-extension    GREEN   ! RSI bearish divergence
  🟡 Failed Breakouts             AMBER   ! win-rate 42%
  🟡 Distribution                 AMBER   ! 5 distribution days / 25d
  🟡 Volatility & News Regime     AMBER   ! vol level 30 · ! hedging into strength
  🔴 Macro / Stagflation          RED     ! PPI 6.5% · ! stagflation · ! margin debt · ! euphoria
```

---

## Using your StockCharts subscription (official breadth data)

The channel reads its breadth off StockCharts, and official series beat our
computed approximations. **Don't automate the login** (their ToS prohibits
robotic access and it risks your subscription) — instead, download the CSVs as
a member and feed the folder to the monitor:

1. Log in at stockcharts.com and open each symbol's chart, then use the
   **Past Data / historical download** member feature to save CSVs:
   `$SPXA50R` (% above 50-day), `$SPXA200R` (% above 200-day),
   `$NYAD` (NYSE advance-decline), `$NYHL` (net new highs-lows),
   and optionally `!GT40SPX` (T2108-style % above 40-day).
2. Save them into one folder, e.g. `~/sc_data/` — filenames just need to
   contain the symbol (`$NYAD.csv`, `nyad.csv`, `NYAD.txt` all work).
3. Run with the folder attached:

```bash
python -m market_barometer.run --source yfinance --stockcharts-dir ~/sc_data
```

Official series **replace** the computed equivalents in the breadth light and
are tagged `[official]` in the panel. Daily routine: refresh the downloads
(a couple of minutes), re-run the command.

---

## Where each input comes from (free sources)

| Input | Free source |
|-------|-------------|
| Index & constituent OHLCV, sector ETFs, VIX | **yfinance** (built in) |
| % above 20/50/200-day, T2108, A-D line | computed from the constituent universe (or StockCharts symbols `$SPXA50R`, `$SPXA200R`, `$NYAD`, `!GT40SPX`) |
| VXN (NASDAQ vol) | `^VXN` via yfinance |
| NFIB small-business optimism | NFIB monthly release / FRED |
| CPI / PPI | BLS / **FRED** (`PPIACO`, `CPIAUCSL`) |
| 10Y/2Y/30Y yields, yield curve | **FRED** (`DGS10`, `DGS2`, `DGS30`, `T10Y2Y`) |
| Margin debt | FINRA monthly |
| CNN Fear & Greed | `production.dataviz.cnn.com/index/fearandgreed/graphdata` |
| Oil / gold / USD (intermarket) | yfinance (`CL=F`, `GC=F`, `DX-Y.NYB`) |

---

## Architecture

```
market_barometer/
├── config.py        # universe, light weights, thresholds, score→stance bands
├── indicators.py    # single-series TA: MA/RSI/MACD/Bollinger/ATR, distance-from-MA,
│                    #   bearish divergence, distribution & high-vol-down days
├── breadth.py       # cross-sectional breadth: % above MA, A-D line, thrust,
│                    #   new highs/lows, up/down volume, sector breadth, rotation,
│                    #   failed-breakout rate
├── barometer.py     # the engine: six lights → Caution Score → stance + regime
├── datasources.py   # MarketData bundle; synthetic (no-network) + yfinance adapters
├── report.py        # terminal rendering of the panel
└── run.py           # CLI
```

The scoring layer is data-source-agnostic: give `compute_barometer()` a
`MarketData` bundle from *any* source and it produces the panel.

---

## Roadmap / how to extend

The methodology in the videos is broader than one weekend of code. Natural next
steps, in priority order:

1. **Full index membership.** Swap the ~40-name `BREADTH_UNIVERSE` for the real
   S&P 500 (or NYSE) constituents so breadth is exact. (`config.py`)
2. **Live macro via FRED.** A `fred.py` adapter to auto-fill NFIB, PPI, yields
   and the yield curve instead of passing them by hand.
3. **Intermarket module.** The cross-asset "something must give" framework
   (stocks vs. bond yields vs. oil vs. USD vs. gold; 30Y-2Y spread; gold vs. its
   7-month EMA) from videos #5–#6, as its own light.
4. **Narrow-leadership gauge.** Concentration metric ("~20 stocks are driving
   the tape, like 2000") and mega-cap-issuing-debt flag.
5. **History & backtest.** Run the barometer over history and chart the Caution
   Score against drawdowns to calibrate thresholds/weights.
6. **Dashboard.** A small HTML/Streamlit front-end with the light panel and
   sparkline history.

Contributions and additional video sources welcome — the thresholds in
`config.py` are meant to be tuned as more of the channel's methodology is
encoded.
