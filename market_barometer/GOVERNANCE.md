# Project Governance & Handoff Guide

This document is the operating manual for anyone — human or AI model —
continuing this project. Read it with `METHODOLOGY.md` before changing code.

## 1. Mission & scope

Build and maintain a **market-timing situation-awareness monitor**: a panel of
weighted warning lights (breadth, over-extension, failed breakouts,
distribution, volatility/news regime, macro overlay) that produces a 0–100
Caution Score and an exposure stance.

**In scope:** signal computation, scoring, reporting, data adapters, backtest
calibration, dashboard front-ends.
**Out of scope (hard limits):** brokerage execution / auto-trading; buy-list or
price-target generation; presenting output as financial advice. Every
user-facing surface must keep the educational-use disclaimer.

## 2. Sources of truth (in priority order)

1. `METHODOLOGY.md` — the distilled trading framework. Code serves it.
2. `config.py` — ALL tunables (universe, weights, thresholds, bands). Never
   hardcode a threshold inside logic; if you need a new number, add it to
   `config.TH` with a comment citing its origin.
3. `tests/test_barometer.py` — the behavioral contract (see §6).

## 3. Architecture rules

Layering (dependencies point downward only):

```
run.py / report.py          (presentation)
        │
barometer.py                (scoring: lights → score → stance)
        │
indicators.py   breadth.py  (pure math, no I/O)
        │
datasources.py              (the ONLY module allowed to touch the network)
```

- `compute_barometer()` must stay **data-source agnostic**: it consumes a
  `MarketData` bundle and must never import from `datasources.py`.
- `indicators.py` / `breadth.py` are **pure functions** on pandas objects — no
  network, no globals, no printing.
- Every check must **degrade gracefully**: missing data → NaN intensity →
  excluded from the score (never a crash, never a fake zero). The `ramp()` +
  `Check`/`Light` pattern handles this; use it.
- New signals follow the recipe in §5.

## 4. Data contracts

`MarketData` (see `datasources.py`):

| Field | Type | Used by |
|---|---|---|
| `index` | DataFrame `open/high/low/close/volume`, DatetimeIndex | momentum, distribution, regime |
| `constituents_close/_volume` | DataFrame, columns = tickers | breadth, failed breakouts |
| `sector_close` | DataFrame, columns = sector ETFs | sector breadth, rotation |
| `vix` | Series | volatility/news regime |
| `vix3m` | Series | VIX term-structure check (VIX/VIX3M) |
| `manual` | dict | overlays below |

Recognized `manual` overlay keys (all optional; absent = check skipped):
`nfib` (float), `ppi_yoy` (float %), `stagflation` (bool),
`yield_10y_rising` (bool), `yield_curve_steepening` (bool),
`yield_curve_uninverting` (bool), `sahm_rule_triggered` (bool),
`credit_spreads_widening` (bool), `put_call_complacent` (bool),
`margin_debt_extreme` (bool), `euphoria` (bool),
`homebuilders_diverging` (bool), `news_reaction_negative` (bool),
`win_rate` (float 0–1).
Adding a key: implement its check in the relevant light, document it here and
in README's macro table, and accept it via `run.py --macro`.

## 5. Recipe: adding a new signal/check

1. Justify it from `METHODOLOGY.md` (or extend that file first, citing the
   source video/material).
2. Implement the raw metric as a pure function in `indicators.py` (per-series)
   or `breadth.py` (cross-sectional), with a docstring linking it to the
   methodology.
3. Add thresholds to `config.TH` as a `(healthy, warning)` ramp pair.
4. Wire a `Check` into the appropriate `_light_*` builder in `barometer.py`
   (or a new light + entry in `config.LIGHT_WEIGHTS`; weights must stay ≈1.0).
5. Make the synthetic `topping` scenario exercise it, and extend the tests.
6. Run the verification gate (§6). Update README tables.

## 6. Verification gate (run before every commit)

```bash
python -m market_barometer.tests.test_barometer     # or: python -m pytest market_barometer/tests -q
python -m market_barometer.run --source synthetic --scenario healthy
python -m market_barometer.run --source synthetic --scenario topping
```

Non-negotiable invariants:
- All tests pass.
- **Discrimination:** healthy < 20 caution / 0 lights / RISK-ON; topping > 40
  caution / ≥4 lights. If a change breaks this, the change is wrong.
- Both CLI runs exit 0 and render the full panel.
- No network calls anywhere except `datasources.yfinance_market` (and future
  adapters).

## 7. Roadmap (priority order, with acceptance criteria)

1. **Full index membership breadth** — replace the ~40-name universe with real
   S&P 500 constituents (fetch or vendored CSV). *Accept:* breadth values
   within a few points of StockCharts `$SPXA50R` on the same date.
2. **FRED macro adapter** (`fred.py`) — auto-fill PPI/CPI (`PPIACO`,
   `CPIAUCSL`), yields (`DGS2/10/30`, `T10Y2Y`), NFIB. *Accept:* macro light
   populates with no `--macro` flags; manual flags still override.
3. **Intermarket light** — the "something must give" cross-asset framework
   (stocks vs oil vs yields vs USD vs gold; 30Y−2Y; gold vs 7-month EMA).
   *Accept:* new light + weight rebalance + tests + METHODOLOGY.md section
   already exists (overlay bullet "cross-asset impossibility").
4. **Concentration/leadership gauge** — top-10 share of index return &
   count of stocks driving gains ("~20 stocks" tell). *Accept:* check inside
   breadth light with test.
5. **History & backtest harness** — run the barometer point-in-time over past
   data; chart Caution Score vs subsequent drawdowns; calibrate `config.TH`
   and weights. *Accept:* notebook/script + a short calibration report; any
   threshold changes justified against 2000, 2007, 2020, 2022 tops.
6. **Dashboard** — Streamlit/HTML panel with lights + score sparkline.
   *Accept:* renders both synthetic scenarios; no framework lock-in leaking
   into the engine.
7. **Zweig Breadth Thrust re-entry signal** — 10d EMA of advancers% crossing
   <40% → >61.5% within 10 sessions; surface as a green "re-entry" banner
   (the monitor should help getting back *in*, not only out). *Accept:*
   detection function + test on a constructed thrust; see RESEARCH.md §1.
8. **Extra canary ratios** — SPHB/SPLV, SMH/SPY, copper/gold as optional
   tickers inside the intermarket light. *Accept:* graceful skip when
   tickers absent.

## 8. Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-07-05 | Warning-light + weighted-score design; no binary calls | Presenter's core principle ("count the lights, don't guess the top") |
| 2026-07-05 | Breadth weighted highest (0.28), momentum 0.24 | Most-emphasised signals across all six videos |
| 2026-07-05 | Synthetic generator as the test bed | Build sandbox blocks all market-data hosts; engine must be provable offline |
| 2026-07-05 | Macro overlay via manual flags first, FRED later | No live macro source in sandbox; keeps engine testable |
| 2026-07-05 | ~40-name curated breadth universe for v1 | Keeps yfinance pulls light; full membership is Roadmap #1 |
| 2026-07-05 | Lives in `market_barometer/` inside crew_rostering repo | Standalone `market-barometer` GitHub repo exists but session integration could not push (403 / approval gate); ready-to-push bundle delivered to owner |
| 2026-07-05 | Community-research round (RESEARCH.md): added McClellan, NH-NL, VIX/VIX3M, XLY/XLP + 4 macro manual keys | Validate video framework against wider practice; only confluence-grade indicators admitted (single-source exotica rejected) |

## 9. Session-environment notes (for future AI sessions)

- The remote build sandbox **blocks market-data hosts** (Yahoo, CNN, stooq —
  403 CONNECT). Package registries work. Develop offline against the
  synthetic scenarios; only the user's machine runs `--source yfinance`.
- GitHub tooling in past sessions was **scoped to this repo only**;
  `create_repository` returned 403 and `add_repo` approval did not clear. The
  standalone repo `manyeesum/market-barometer` exists (empty); a git bundle
  with the project at repo-root layout was delivered to the owner. If a future
  session gains access, push that layout (package dir + README/requirements at
  root) to `main`.
- YouTube transcripts cannot be fetched by tooling; the owner pastes them into
  chat. When new transcripts arrive: distill → update `METHODOLOGY.md` first,
  then implement per §5. Do not store raw transcripts in the repo.

## 10. Handoff checklist (start-of-session)

1. Read `METHODOLOGY.md`, this file, and `README.md`.
2. Run the verification gate (§6) to confirm a green baseline.
3. Pick the top unblocked roadmap item (§7) unless the owner directs
   otherwise.
4. Follow §5 for any new signal; keep §6 green; append to §8 for any
   non-obvious decision.
5. Commit to the designated branch and push; never force-push shared history.
