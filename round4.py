"""Round 4: regime / breadth / credit / vol-risk-premium hypotheses. Run: python3 round4.py"""
import numpy as np
import pandas as pd
from harness import (load, close, single_asset_strategy, multi_asset_strategy,
                     stats, fmt_table, month_end_mask, turn_of_month_mask, cost_of)

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

# H25 Vol risk premium: SVXY when VIX<20, else cash (includes Feb-2018 crash)
vix = None
for v in ["vix", "vix.us"]:
    try:
        vix = close(v)
        break
    except Exception:
        pass
if vix is not None:
    try:
        svxy = close("svxy.us")
        pos = (vix < 20).astype(float).reindex(svxy.index).ffill().fillna(0.0)
        results.append(stats(single_asset_strategy(pos, svxy, cash, cost=3e-4), bench, "H25 SVXY when VIX<20"))
    except Exception as e:
        print(f"[skip H25] {e}")

# H28 Sector breadth gate: long SPY when >=5 of 9 sectors above their MA200
secs = ["xlk.us", "xlf.us", "xle.us", "xlv.us", "xli.us", "xlp.us", "xlu.us", "xly.us", "xlb.us"]
try:
    C = pd.concat([close(s) for s in secs], axis=1).dropna()
    above = (C > C.rolling(200).mean()).sum(axis=1)
    pos = (above >= 5).astype(float).reindex(c.index).fillna(0.0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H28 Breadth>=5/9 gate"))
    # variant: breadth as sizing 0..1
    pos2 = (above / 9.0).reindex(c.index).fillna(0.0)
    pos2 = (pos2 * 10).round() / 10
    results.append(stats(single_asset_strategy(pos2, c, cash, sym="spy.us"), bench, "H28b Breadth-sized"))
except Exception as e:
    print(f"[skip H28] {e}")

# H29 Credit regime: long SPY when HYG 63d return > LQD 63d return
try:
    hyg = close("hyg.us")
    lqd = close("lqd.us")
    idxc = hyg.index.intersection(lqd.index)
    sig = ((hyg / hyg.shift(63) - 1).reindex(idxc) > (lqd / lqd.shift(63) - 1).reindex(idxc))
    pos = sig.astype(float).reindex(c.index).ffill().fillna(0.0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H29 Credit-regime gate"))
except Exception as e:
    print(f"[skip H29] {e}")

# H32 UPRO (3x) + MA200 trend gate
try:
    upro = close("upro.us")
    pos = (c > ma200).astype(float).reindex(upro.index).fillna(0.0)
    results.append(stats(single_asset_strategy(pos, upro, cash, sym="upro.us"), bench, "H32 UPRO + MA200"))
except Exception as e:
    print(f"[skip H32] {e}")

# H33 3-day pullback dip-buy in uptrend, exit after 5 days or new 10d high
cond_enter = ((c < c.shift(1)) & (c.shift(1) < c.shift(2)) & (c.shift(2) < c.shift(3)) & (c > ma200)).values
hi10 = (c >= c.rolling(10).max()).values
state = np.zeros(len(c))
holding = 0
for i in range(len(c)):
    if holding > 0:
        holding += 1
        if hi10[i] or holding > 5:
            holding = 0
    if holding == 0 and cond_enter[i]:
        holding = 1
    state[i] = 1.0 if holding > 0 else 0.0
pos = pd.Series(state, index=c.index)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H33 3d pullback buy"))

# H34 TOM + trend + leverage: SSO during TOM only when SPY>MA200, else SHY
try:
    sso = close("sso.us")
    tom = turn_of_month_mask(sso.index).astype(float).shift(-1).fillna(0.0)
    gate = (c > ma200).astype(float).reindex(sso.index).fillna(0.0)
    pos = tom * gate
    results.append(stats(single_asset_strategy(pos, sso, cash, sym="sso.us"), bench, "H34 SSO TOM+trend"))
except Exception as e:
    print(f"[skip H34] {e}")

print(fmt_table(results))
pd.DataFrame(results).to_csv("round4_results.csv", index=False)
print("saved round4_results.csv")
