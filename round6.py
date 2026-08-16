"""Round 6: option-strategy indices, VIX term structure, true shorts. Run: python3 round6.py"""
import numpy as np
import pandas as pd
from harness import (load, close, single_asset_strategy, multi_asset_strategy,
                     stats, fmt_table, cost_of)

spy = load("spy.us")
c = spy["Close"]
bench = c.pct_change().dropna().rename("spy")
try:
    shy = close("shy.us").pct_change()
except Exception:
    shy = pd.Series(0.0, index=c.index)
cash = shy.reindex(c.index).fillna(0.0)
results = []
ma200 = c.rolling(200).mean()


def maybe(sym):
    try:
        return close(sym)
    except Exception:
        return None


# H40-H43: CBOE option-strategy indices, buy & hold vs SPY
# (index levels; add ~15bp/yr implementation drag as daily haircut)
DRAG = 0.0015 / 252
for sym, nm in [("put", "H40 PUT put-write idx"), ("bxm", "H41 BXM covered-call"),
                ("bxy", "H41b BXY 2%OTM cc"), ("cll", "H42 CLL collar"),
                ("cndr", "H43 CNDR condor")]:
    ser = maybe(sym)
    if ser is None:
        print(f"[skip {nm}] no data")
        continue
    results.append(stats((ser.pct_change() - DRAG).dropna(), bench, nm))

# H44: SVXY only in contango (VIX3M > VIX), else cash; needs vix3m
vix = maybe("vix")
if vix is None:
    vix = maybe("vix.us")
vix3m = maybe("vix3m")
svxy = maybe("svxy.us")
if vix is not None and vix3m is not None and svxy is not None:
    slope = (vix3m / vix).dropna()
    pos = (slope > 1.0).astype(float).reindex(svxy.index).ffill().fillna(0.0)
    results.append(stats(single_asset_strategy(pos, svxy, cash, cost=3e-4), bench, "H44 SVXY contango-only"))
else:
    print("[skip H44] missing vix3m/svxy")

# H44b: tail overlay — SPY always + 10% VIXY when backwardation
vixy = maybe("vixy.us")
if vix is not None and vix3m is not None and vixy is not None:
    idx = c.index.intersection(vixy.index)
    slope = (vix3m / vix).reindex(idx).ffill()
    w_v = (slope < 1.0).astype(float) * 0.10
    W = pd.DataFrame({"spy.us": 1.0, "vixy.us": w_v}, index=idx)
    duo = pd.concat([c.reindex(idx), vixy.reindex(idx)], axis=1)
    duo.columns = ["spy.us", "vixy.us"]
    results.append(stats(multi_asset_strategy(W, duo, cash, costs={"spy.us": 1e-4, "vixy.us": 3e-4}),
                         bench, "H44b SPY+VIXY tail timing"))

# H45: long/short trend on SPY (+1 above MA200 / -1 below), and half-short variant
pos = pd.Series(np.where(c > ma200, 1.0, -1.0), index=c.index)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H45 L/S trend +1/-1"))
pos = pd.Series(np.where(c > ma200, 1.0, -0.5), index=c.index)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H45b L/S trend +1/-0.5"))

# H46: risk-managed add-on: 1.0 SPY + 0.5 more only when trend on AND vol < median
rv = bench.rolling(20).std() * np.sqrt(252)
rv_med = rv.expanding(252).median()
addon = ((c > ma200).astype(float) * (rv < rv_med).astype(float) * 0.5)
pos = (1.0 + addon).fillna(1.0)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H46 calm-uptrend 1.5x"))

# H47: QQQ/TLT relative-momentum barbell (63d), monthly-ish via signal persistence
q = maybe("qqq.us")
tlt = maybe("tlt.us")
if q is not None and tlt is not None:
    idx = q.index.intersection(tlt.index)
    relq = (q / q.shift(63) - 1).reindex(idx)
    relt = (tlt / tlt.shift(63) - 1).reindex(idx)
    pick_q = (relq > relt).astype(float)
    # rebalance only on month end to limit turnover
    from harness import month_end_mask
    me = month_end_mask(idx)
    sel = pick_q.where(me, np.nan).ffill().fillna(0.0)
    W = pd.DataFrame({"qqq.us": sel, "tlt.us": 1.0 - sel}, index=idx)
    duo = pd.concat([q.reindex(idx), tlt.reindex(idx)], axis=1)
    duo.columns = ["qqq.us", "tlt.us"]
    results.append(stats(multi_asset_strategy(W, duo, cash), bench, "H47 QQQ/TLT barbell"))

print(fmt_table(results))
pd.DataFrame(results).to_csv("round6_results.csv", index=False)
print("saved round6_results.csv")
