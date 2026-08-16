"""Round 5: cross-sectional stock tests on a SURVIVORSHIP-BIASED universe.
The bias inflates every long-only result vs SPY, therefore:
  - a FAIL here is a strong reject
  - a PASS here is NOT an accept (bias could explain it) — marked accordingly.
Run: python3 round5.py
"""
import glob
import os
import numpy as np
import pandas as pd
from harness import (load, close, multi_asset_strategy, stats, fmt_table,
                     month_end_mask, DATA)

spy = load("spy.us")
c = spy["Close"]
bench = c.pct_change().dropna().rename("spy")
try:
    shy = close("shy.us").pct_change()
except Exception:
    shy = pd.Series(0.0, index=c.index)
cash = shy.reindex(c.index).fillna(0.0)

STOCKS = [s.strip() for s in """aapl.us msft.us ibm.us ge.us ko.us pg.us jnj.us xom.us cvx.us wmt.us
jpm.us bac.us wfc.us c.us mrk.us pfe.us intc.us csco.us orcl.us hd.us mcd.us dis.us ba.us cat.us
mmm.us hon.us ups.us fdx.us nke.us sbux.us txn.us qcom.us amgn.us gild.us adbe.us crm.us nvda.us
amd.us mu.us t.us vz.us cmcsa.us pep.us cl.us kmb.us mo.us abt.us bmy.us lly.us unh.us cvs.us
axp.us gs.us ms.us usb.us pnc.us tgt.us low.us cost.us emr.us""".split()]

closes = []
for s in STOCKS:
    try:
        ser = close(s)
        if len(ser) > 2520:
            closes.append(ser)
    except Exception:
        pass
print(f"[universe] {len(closes)} stocks loaded")
C = pd.concat(closes, axis=1)
C = C[C.index >= "1995-01-01"]
R = C.pct_change()
me = month_end_mask(C.index)
STOCK_COST = 5e-4  # 5 bp/side
results = []


def run_cs(rank_scores, k, name, ascending=False):
    """Long top-k equal weight by score, monthly rebalance."""
    W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    sc = rank_scores[me]
    ranks = sc.rank(axis=1, ascending=ascending)
    live = sc.notna().sum(axis=1)
    w_me = (ranks <= k).astype(float)
    w_me = w_me.div(w_me.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    # require at least 20 live names else stay in cash
    w_me[live < 20] = 0.0
    W[me] = w_me
    W[~me] = np.nan
    W = W.ffill().fillna(0.0)
    costs = {col: STOCK_COST for col in C.columns}
    sr = multi_asset_strategy(W, C, cash, costs=costs)
    results.append(stats(sr, bench, name))


# H35 CS momentum 12-1, top 6
mom = C.shift(21) / C.shift(252) - 1
run_cs(mom, 6, "H35 CS mom 12-1 top6")
# H35b top 12 (less concentrated)
run_cs(mom, 12, "H35b CS mom 12-1 top12")

# H36 CS low-vol: bottom 12 by 126d vol (ascending rank = lowest vol first)
vol = R.rolling(126).std()
run_cs(vol, 12, "H36 CS low-vol bottom12", ascending=True)

# H37 CS 52w-high proximity top 12
prox = C / C.rolling(252).max()
run_cs(prox, 12, "H37 CS 52w-high top12")

# H38 CS short-term reversal: worst 12 over past 21d (ascending: most negative first)
st = C / C.shift(21) - 1
run_cs(st, 12, "H38 CS 1m reversal worst12")

print(fmt_table(results))
print("\nNOTE: survivorship-biased universe — FAIL=strong reject; PASS=not evidence.")
pd.DataFrame(results).to_csv("round5_results.csv", index=False)
print("saved round5_results.csv")
