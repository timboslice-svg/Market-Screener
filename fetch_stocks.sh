#!/bin/bash
# Batch 3: ~60 long-history US large caps (SURVIVORSHIP-BIASED universe — reject-only tests)
cd "$(dirname "$0")"
mkdir -p data
SYMBOLS="aapl.us msft.us ibm.us ge.us ko.us pg.us jnj.us xom.us cvx.us wmt.us jpm.us bac.us wfc.us c.us mrk.us pfe.us intc.us csco.us orcl.us hd.us mcd.us dis.us ba.us cat.us mmm.us hon.us ups.us fdx.us nke.us sbux.us txn.us qcom.us amgn.us gild.us adbe.us crm.us nvda.us amd.us mu.us t.us vz.us cmcsa.us pep.us cl.us kmb.us mo.us abt.us bmy.us lly.us unh.us cvs.us axp.us gs.us ms.us usb.us pnc.us tgt.us low.us cost.us emr.us"
for s in $SYMBOLS; do
  f="data/$(echo "$s" | tr -d '^').csv"
  if [ -s "$f" ] && head -1 "$f" | grep -qi date; then
    echo "$s,cached" >> data/MANIFEST3.txt
    continue
  fi
  curl -s --max-time 30 "https://stooq.com/q/d/l/?s=${s}&i=d" -o "$f"
  rows=$(wc -l < "$f" | tr -d ' ')
  if head -1 "$f" | grep -qi "date"; then ok="ok"; else ok="BAD"; fi
  echo "$s,$f,$rows,$ok" >> data/MANIFEST3.txt
  sleep 1
done
echo "stocks fetched: $(wc -l < data/MANIFEST3.txt)"
