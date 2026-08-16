#!/bin/bash
# Fetch daily history CSVs from Stooq into ./data/
cd "$(dirname "$0")"
mkdir -p data
SYMBOLS="spy.us qqq.us iwm.us dia.us efa.us eem.us ^spx ^ndx tlt.us ief.us shy.us agg.us lqd.us hyg.us xlk.us xlf.us xle.us xlv.us xli.us xlp.us xlu.us xly.us xlb.us mtum.us vlue.us qual.us usmv.us splv.us sphb.us ijs.us vug.us vtv.us sso.us upro.us gld.us vnq.us ^vix vix.us"
for s in $SYMBOLS; do
  f="data/$(echo "$s" | tr -d '^').csv"
  curl -s --max-time 30 "https://stooq.com/q/d/l/?s=${s}&i=d" -o "$f"
  rows=$(wc -l < "$f" | tr -d ' ')
  first=$(sed -n '2p' "$f" | cut -d, -f1)
  last=$(tail -1 "$f" | cut -d, -f1)
  if head -1 "$f" | grep -qi "date"; then ok="ok"; else ok="BAD"; fi
  echo "$s,$f,$rows,$first,$last,$ok" | tee -a data/MANIFEST.txt
  sleep 1
done
echo "--- SPY first rows (adjustment check) ---"
head -4 data/spy.us.csv
echo "--- SPY last row ---"
tail -1 data/spy.us.csv
