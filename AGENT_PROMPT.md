# Standalone prompt — run the nightly screener in any Claude Code session

Paste everything below into a fresh Claude Code session (any model) if the main
session's tools are unavailable:

---

Run my nightly market screener end-to-end. Working directory:
`~/Documents/6_Business/7_Trading_Bot/equity_research_2026-07/screener`
(if that doesn't exist, use the copy under /private/tmp/claude-501/*/scratchpad/screener).

Steps:
1. `python3 scan.py` — downloads prices via yfinance, flags unusual idiosyncratic moves.
2. `python3 news.py` — pulls Google News + Yahoo RSS headlines per flag.
3. `python3 ledger.py` — appends flags to the ledger, fills forward returns of old flags.
4. YOU do the triage (read `PROMPT.md` for the rubric): read `flags.json` + `news.json`,
   write `triage.json` — array of {ticker, category: real-deterioration|real-improvement|
   flow-or-sentiment|unclear, interesting: 0-10, rationale (2 sentences citing headlines),
   cited: [headline indices]}. Research triage only, never buy/sell advice.
5. `python3 dashboard.py` — renders dashboard.html.
6. Report: how many flags, the top 5 by interestingness with one line each, and the
   ledger's running hit-rate line if it printed one.

If yfinance hits rate limits, wait 60s and retry the failed step once.
