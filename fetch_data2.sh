#!/bin/bash
# Batch 2: country ETFs + equal-weight + misc for round 3
cd "$(dirname "$0")"
mkdir -p data
SYMBOLS="rsp.us ewj.us ewg.us ewu.us ewq.us ewa.us ewc.us ewh.us ews.us eww.us ewz.us fxi.us ewt.us ewy.us ewl.us ewp.us ewi.us ewd.us ewn.us ewo.us ewk.us eza.us svxy.us vixy.us"
for s in $SYMBOLS; do
  f="data/$(echo "$s" | tr -d '^').csv"
  curl -s --max-time 30 "https://stooq.com/q/d/l/?s=${s}&i=d" -o "$f"
  rows=$(wc -l < "$f" | tr -d ' ')
  first=$(sed -n '2p' "$f" | cut -d, -f1)
  last=$(tail -1 "$f" | cut -d, -f1)
  if head -1 "$f" | grep -qi "date"; then ok="ok"; else ok="BAD"; fi
  echo "$s,$f,$rows,$first,$last,$ok" | tee -a data/MANIFEST2.txt
  sleep 1
done
