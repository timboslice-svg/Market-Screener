#!/bin/bash
# Batch 4: option-strategy indices (CBOE), VIX term structure, vol ETPs
cd "$(dirname "$0")"
mkdir -p data
SYMBOLS="^put ^bxm ^bxy ^cll ^cndr ^vix3m ^vvix vxz.us vixm.us smh.us iyt.us es.f nq.f ty.f zn.f gc.f cl.f dx.f vx.f si.f hg.f"
for s in $SYMBOLS; do
  f="data/$(echo "$s" | tr -d '^').csv"
  curl -s --max-time 30 "https://stooq.com/q/d/l/?s=${s}&i=d" -o "$f"
  rows=$(wc -l < "$f" | tr -d ' ')
  first=$(sed -n '2p' "$f" | cut -d, -f1)
  last=$(tail -1 "$f" | cut -d, -f1)
  if head -1 "$f" | grep -qi "date"; then ok="ok"; else ok="BAD"; fi
  echo "$s,$f,$rows,$first,$last,$ok" | tee -a data/MANIFEST4.txt
  sleep 1
done
