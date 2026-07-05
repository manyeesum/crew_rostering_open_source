# 📖 Beginner's Guide — running your Market Barometer step by step

*Written for a non-programmer. Every command below is copy-paste — you never
need to write code. Commands go into the **Terminal** app (Mac) or
**PowerShell** (Windows: press Start, type "powershell", press Enter).*

---

## Part 1 — One-time setup (about 10 minutes, done once ever)

**Step 1. Install Python** (the free program that runs the monitor)
- Go to https://www.python.org/downloads/ and click the big yellow button.
- Windows only: on the installer's first screen, **tick the box
  "Add Python to PATH"** before clicking Install. This matters.
- Mac: just run the installer.

**Step 2. Put the project somewhere easy**
- Unzip the `market-barometer.tar.gz` file you downloaded from our chat
  (double-click on Mac; right-click → Extract All on Windows).
- Move the resulting `market-barometer` folder into your home folder or
  Documents. Remember where it is.

**Step 3. Open a terminal *inside* that folder**
- Mac: open Terminal, type `cd ` (with a space), drag the
  `market-barometer` folder onto the Terminal window, press Enter.
- Windows: open the `market-barometer` folder in File Explorer, click the
  address bar, type `powershell`, press Enter.

**Step 4. Install the helper packages** (copy-paste, press Enter, wait):

```
pip install -r requirements.txt
```

**Step 5. Test that everything works** — this uses built-in fake data, no
internet needed:

```
python -m market_barometer.run --source synthetic --scenario topping
```

You should see the barometer panel with a score around 43/100 and warning
lights. If you see that — setup is done forever. 🎉

---

## Part 2 — Your DAILY routine (2–5 minutes)

### Step A. Download the StockCharts files (the official breadth data)

Log in to stockcharts.com **yourself, in your browser** (never give the
password to any program or bot — their rules forbid automated access and it
could cost you your subscription).

For each symbol in the table below: bring up its chart, open the **"Past
Data"** view under the chart (a members' feature that shows the data table)
and download/save it as a CSV file. If a symbol only shows a table with no
download button, select the table, copy, and paste into a plain text file —
the monitor reads that fine as long as it has a Date column and a Close
column.

**THE SHOPPING LIST — exactly 4 files, saved into one folder** (e.g. a folder
called `sc_data` inside your `market-barometer` folder):

| # | Symbol to type into StockCharts | What it is | Save the file as |
|---|---|---|---|
| 1 | `$SPXA50R` | % of S&P 500 stocks above their 50-day average — the "participation" gauge (healthy >60%, danger <40%) | `SPXA50R.csv` |
| 2 | `$SPXA200R` | % above their 200-day average — long-term participation | `SPXA200R.csv` |
| 3 | `$NYAD` | NYSE Advance-Decline — the daily count of rising vs falling stocks; its trend line is the classic top-warning | `NYAD.csv` |
| 4 | `$NYHL` | NYSE net new 52-week highs minus lows — negative while the index is at highs = "split tape" danger | `NYHL.csv` |

*Optional 5th:* `$NYA50R` (% of ALL NYSE stocks above 50-day — a broader
version of #1). Save as `NYA50R.csv`.

Notes that make this painless:
- Capitalization and the `$` sign in filenames don't matter — `nyad.csv`,
  `NYAD.csv` and `$NYAD.csv` all work.
- You do **not** need to download prices for SPY, sectors or VIX — the
  monitor fetches all of those automatically from Yahoo Finance.
- Missed a day? Nothing breaks. The monitor just uses the computed backup
  numbers for anything missing and marks official data with `[official]`
  when present.

### Step B. Run the monitor (one line, copy-paste)

```
python -m market_barometer.run --source yfinance --stockcharts-dir sc_data --save-history
```

That single line: fetches market prices → reads your StockCharts files →
scores all six lights → prints the panel → saves today's score into
`barometer_history.csv` → shows your recent trend.

### Step C. Read the result (10 seconds)

Look at three things, top of the printout:

1. **CAUTION SCORE** (0–100) and **STANCE**:

| Score | Stance | What it means for you |
|---|---|---|
| 0–20 | RISK-ON | Healthy market — normal investing |
| 20–40 | CONSTRUCTIVE | Fine, but keep your stop-losses in place |
| 40–60 | CAUTION | Trim winners, no leverage, smaller new buys |
| 60–80 | DEFENSIVE | Raise cash seriously, no new buying |
| 80–100 | RISK-OFF | Preservation mode — the music has stopped |

2. **Lights lit (x/6)** — the core rule from the videos: *more lights on =
   trim more*. One amber light is noise; four lights is a message.
3. **The ⚠ LIT WARNINGS list** — tells you *which* specific things worry the
   monitor today, in plain sentences.

The history at the bottom shows whether the score is *rising over the weeks*
— a score drifting 15 → 30 → 45 is exactly the "top forming" pattern.

---

## Part 3 — MONTHLY: update the big-picture switches (5 minutes)

Some things can't be downloaded automatically (economy data, sentiment).
They're simple yes/no switches or one number, added to the command. Once a
month, answer these questions:

| Question to ask yourself | Where to look (free) | If YES, add this to the command |
|---|---|---|
| Is producer inflation (PPI) hot, above ~4% yearly? | Search "US PPI YoY" — tradingeconomics.com or FRED | `ppi_yoy=6.5` (use the actual number) |
| Is small-business optimism (NFIB) below ~98? | Search "NFIB optimism index" | `nfib=95.3` (actual number) |
| High inflation AND slowing economy at the same time? | News judgment | `stagflation=1` |
| Are 10-year bond yields climbing hard? | Search "US 10 year treasury yield" | `yield_10y_rising=1` |
| Did the yield curve just un-invert (2s10s turning positive after being negative)? | FRED chart "T10Y2Y" | `yield_curve_uninverting=1` |
| Sahm rule triggered (unemployment clearly rising off its low)? | Search "Sahm rule FRED" | `sahm_rule_triggered=1` |
| Are junk-bond (high-yield) spreads widening? | FRED chart "BAMLH0A0HYM2" | `credit_spreads_widening=1` |
| Is margin debt at record levels? | Search "FINRA margin debt" | `margin_debt_extreme=1` |
| Is retail sentiment euphoric (FOMO, leveraged-ETF mania)? | Your own judgment + CNN Fear & Greed | `euphoria=1` |
| Are homebuilder stocks (XHB) badly lagging the market? | Any chart site, XHB vs SPY | `homebuilders_diverging=1` |
| Is the market now DROPPING on bad news it used to ignore? | Your observation | `news_reaction_negative=1` |

String the ones that apply onto the daily command after `--macro`, separated
by commas. Full example:

```
python -m market_barometer.run --source yfinance --stockcharts-dir sc_data --save-history --macro ppi_yoy=6.5,nfib=95.3,stagflation=1,margin_debt_extreme=1,euphoria=1
```

Leave out anything that's a "no" — an absent switch simply isn't scored.
Keep your current `--macro` text saved in a note; update it monthly.

---

## Part 4 — Your history chart

Every `--save-history` run adds one line to **`barometer_history.csv`** in
the project folder. Double-click it — it opens in Excel / Numbers / Google
Sheets. Chart the `caution_score` column over time and you have your own
market-top early-warning chart, exactly like the channel's approach.

---

## Troubleshooting (the three errors beginners actually hit)

| You see... | Fix |
|---|---|
| `python: command not found` / `'python' is not recognized` | Python isn't installed or PATH box wasn't ticked. Reinstall from python.org WITH "Add to PATH" ticked. On Mac try `python3` instead of `python`. |
| `No module named pandas` (or yfinance) | Run the install line again: `pip install -r requirements.txt` (Mac: `pip3`). |
| `StockCharts data folder not found` | The folder name/location doesn't match. If your folder is `sc_data` inside the project, use exactly `--stockcharts-dir sc_data`. |
| yfinance errors / blank prices | Yahoo hiccup or no internet — wait and re-run; the monitor still works with whatever loaded. |

---

*Reminder: this is an educational situation-awareness tool, not financial
advice. It measures conditions; decisions stay yours.*
