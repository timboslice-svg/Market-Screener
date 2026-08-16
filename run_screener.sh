#!/bin/bash
# Nightly screener pipeline. Run after US close (~22:15 CET) — at that moment the
# latest completed sessions of Asia, Europe AND the US are all available.
cd "$(dirname "$0")"
set -e
python3 scan.py
python3 overview.py
python3 news.py
python3 ledger.py
python3 events_cal.py || echo "calendar failed (non-fatal)"
if [ -n "$OPENROUTER_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
  python3 triage_api.py || echo "triage failed — dashboard will show raw flags"
else
  echo "no OPENROUTER_API_KEY / ANTHROPIC_API_KEY — skipping AI triage (see PROMPT.md)"
fi
python3 dashboard.py
echo "done: open $(pwd)/dashboard.html"
