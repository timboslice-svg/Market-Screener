"""Round 3: the more creative / structural hypotheses. Run: python3 round3.py"""
import numpy as np
import pandas as pd
from harness import (load, close, single_asset_strategy, multi_asset_strategy,
                     stats, fmt_table, month_end_mask, cost_of)

spy = load("spy.us")
c = spy["Close"]
bench = c.pct_change().dropna().rename("spy")
try:
    shy = close("shy.us").pct_change()
except Exception:
    shy = pd.Series(0.0, index=c.index)
cash = shy.reindex(c.index).fillna(0.0)

results = []

# H15 RSP equal-weight S&P vs SPY
try:
    results.append(stats(close("rsp.us").pct_change().dropna(), bench, "H15 RSP equal-weight B&H"))
except Exception as e:
    print(f"[skip H15] {e}")

# H16 Country-ETF momentum: top 3 of universe by 12-1, monthly
ctys = ["ewj.us", "ewg.us", "ewu.us", "ewq.us", "ewa.us", "ewc.us", "ewh.us",
        "ews.us", "eww.us", "ewz.us", "fxi.us", "ewt.us", "ewy.us", "ewl.us",
        "ewp.us", "ewi.us", "ewd.us", "ewn.us", "ewo.us", "ewk.us", "eza.us"]
loaded = []
for s in ctys:
    try:
        loaded.append(close(s))
    except Exception:
        pass
if len(loaded) >= 8:
    C = pd.concat(loaded, axis=1)
    C = C.dropna(thresh=8)  # need at least 8 live ETFs
    mom = C.shift(21) / C.shift(252) - 1
    me = month_end_mask(C.index)
    W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    ranks = mom[me].rank(axis=1, ascending=False)
    W[me] = (ranks <= 3).astype(float) / 3.0
    W[~me] = np.nan
    W = W.ffill().fillna(0.0)
    results.append(stats(multi_asset_strategy(W, C, cash), bench, "H16 Country mom top3"))
else:
    print(f"[skip H16] only {len(loaded)} country ETFs")

# H17 Sell-in-May: long SPY Nov-Apr, cash May-Oct
pos = pd.Series((c.index.month <= 4) | (c.index.month >= 11), index=c.index).astype(float)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H17 Sell-in-May"))

# H18 Return stacking 90/60 SPY/TLT (NTSX-style), monthly rebalance
try:
    duo = pd.concat([close("spy.us"), close("tlt.us")], axis=1).dropna()
    duo.columns = ["spy.us", "tlt.us"]
    me = month_end_mask(duo.index)
    W = pd.DataFrame(np.nan, index=duo.index, columns=duo.columns)
    W.loc[me, "spy.us"] = 0.9
    W.loc[me, "tlt.us"] = 0.6
    W = W.ffill().fillna(0.0)
    results.append(stats(multi_asset_strategy(W, duo, cash), bench, "H18 90/60 SPY/TLT stack"))
except Exception as e:
    print(f"[skip H18] {e}")

# H19 GLD/SPY relative momentum, monthly
try:
    duo = pd.concat([close("spy.us"), close("gld.us")], axis=1).dropna()
    duo.columns = ["spy.us", "gld.us"]
    m12 = duo / duo.shift(252) - 1
    me = month_end_mask(duo.index)
    W = pd.DataFrame(np.nan, index=duo.index, columns=duo.columns)
    pick_spy = (m12["spy.us"] >= m12["gld.us"])[me]
    W.loc[me, "spy.us"] = pick_spy.astype(float)
    W.loc[me, "gld.us"] = (~pick_spy).astype(float)
    W = W.ffill().fillna(0.0)
    results.append(stats(multi_asset_strategy(W, duo, cash), bench, "H19 SPY/GLD momentum"))
except Exception as e:
    print(f"[skip H19] {e}")

# H20 52-week-high proximity: long when close >= 95% of 252d max
prox = c / c.rolling(252).max()
pos = (prox >= 0.95).astype(float)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H20 52w-high proximity"))

# H21 Lever-the-dips: 1.0x normally; 1.5x while drawdown>15% until new high
dd = c / c.cummax() - 1
lev = np.where(dd < -0.15, 1.5, np.nan)
# stay levered until new ATH (dd==0) after trigger
state = np.ones(len(c))
levered = False
ddv = dd.values
for i in range(len(c)):
    if not levered and ddv[i] < -0.15:
        levered = True
    elif levered and ddv[i] >= -0.001:
        levered = False
    state[i] = 1.5 if levered else 1.0
pos = pd.Series(state, index=c.index)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H21 Lever-the-dips 1.5x"))

# H22 VIX-spike crisis alpha: SPY normally, SSO after VIX>35 until VIX<25
vix = None
for v in ["vix", "vix.us"]:
    try:
        vix = close(v)
        break
    except Exception:
        pass
if vix is not None:
    try:
        sso = close("sso.us")
        idx = c.index.intersection(sso.index)
        vv = vix.reindex(idx).ffill()
        state = np.zeros(len(idx))
        on = False
        for i, dt in enumerate(idx):
            x = vv.iloc[i]
            if not on and x > 35:
                on = True
            elif on and x < 25:
                on = False
            state[i] = 1.0 if on else 0.0
        w_sso = pd.Series(state, index=idx)
        duo = pd.concat([c.reindex(idx), sso.reindex(idx)], axis=1)
        duo.columns = ["spy.us", "sso.us"]
        W = pd.DataFrame({"spy.us": 1.0 - w_sso, "sso.us": w_sso}, index=idx)
        results.append(stats(multi_asset_strategy(W, duo, cash), bench, "H22 VIX-spike -> 2x"))
    except Exception as e:
        print(f"[skip H22] {e}")

# H23 Trend + vol-managed combo (gate * scaling, cap 2)
rv = bench.rolling(20).std() * np.sqrt(252)
ma200 = c.rolling(200).mean()
gate = (c > ma200).astype(float)
scale = ((0.17 ** 2) / rv ** 2).clip(0, 2)
pos = (gate * scale.reindex(c.index)).fillna(0.0)
pos = (pos * 10).round() / 10
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H23 Trend x VolMgd cap2"))

# H24 QQQ with MA200 trend gate (on QQQ itself)
try:
    q = close("qqq.us")
    qma = q.rolling(200).mean()
    pos = (q > qma).astype(float)
    results.append(stats(single_asset_strategy(pos, q, cash, sym="qqq.us"), bench, "H24 QQQ + MA200"))
except Exception as e:
    print(f"[skip H24] {e}")

print(fmt_table(results))
pd.DataFrame(results).to_csv("round3_results.csv", index=False)
print("saved round3_results.csv")
