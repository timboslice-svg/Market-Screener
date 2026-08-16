# Nightly market screener v0 — "filtered financial news channel"

Scans ~160 large caps across US / DE / FR / UK / JP / AU / SG for **idiosyncratic**
moves (unusual vs the stock's own volatility AND its regional index), pulls free
headlines for every flag, optionally has Claude triage what's actually interesting,
renders a dashboard, and keeps a self-evaluation ledger.

**Free data only:** yfinance (prices, global), Google News RSS + Yahoo RSS (headlines).
AI triage is optional: `ANTHROPIC_API_KEY` + `triage_api.py`, or a Claude Code
scheduled agent following `PROMPT.md` (no API key needed).

## Run

    ./run_screener.sh          # then open dashboard.html

One run takes ~3-5 min (rate-limit-friendly pacing). Run after US close (~22:15 CET):
at that moment the most recent completed sessions of Asia, Europe and the US are all in.

## Files

- `universe.csv` — tickers/names/regions/benchmarks. Edit freely; v0 is a large-cap
  seed list (~160 names). Expansion path: full index constituent lists.
- `scan.py` — stage 1: anomaly scan (z-scores of idiosyncratic 1d/5d moves, volume
  spikes, 52w position) → `flags.json` (top 40)
- `news.py` — stage 2: headlines per flag → `news.json`
- `triage_api.py` — optional stage 3: Claude classifies each flag
  (real-deterioration / flow-or-sentiment / unclear + interestingness 0-10) → `triage.json`
- `dashboard.py` — renders `dashboard.html` (cards sorted by interestingness, article links)
- `ledger.py` — appends every flag, fills 5/20-day forward excess returns on later runs,
  prints the running hit rate. **This is the part that proves or disproves the screener.**

## Scheduling

macOS launchd (nightly 22:15): create `~/Library/LaunchAgents/com.tim.screener.plist`
with a ProgramArguments entry running `run_screener.sh`, or ask Claude Code to set up
a scheduled agent that runs the pipeline AND does the triage itself per `PROMPT.md`.

## Design notes / honesty

- This is an attention filter, not a signal engine. The research loop (see
  `../PROTOCOL.md`, round 11) showed price-only "oversold" has no reliable edge —
  and drops in previously-healthy stocks specifically do NOT rebound. Whatever value
  this tool has comes from the news classification + your judgment.
- The ledger is non-negotiable: after ~3 months it will tell you whether
  high-interestingness down-flags actually outperform. If they don't, kill or revise.
- Known v0 limits: headlines only (no article bodies/paywalls), no fundamentals feed,
  universe is a seed list, single nightly run (fine for a daily brief).
