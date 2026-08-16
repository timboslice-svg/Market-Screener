"""Round 1 hypothesis battery. Run: python3 round1.py"""
import numpy as np
import pandas as pd
from harness import (load, close, single_asset_strategy, multi_asset_strategy,
                     stats, fmt_table, rsi, month_end_mask, turn_of_month_mask,
                     cost_of, DATA)

pd.set_option("display.width", 200)

spy = load("spy.us")
c = spy["Close"]
o = spy["Open"]
bench = c.pct_change().dropna().rename("spy")

try:
    shy = close("shy.us").pct_change()
except Exception:
    shy = pd.Series(0.0, index=c.index)
cash = shy.reindex(c.index).fillna(0.0)

results = []

# --- Sanity: overnight+intraday decomposition should reconstruct close-to-close
on_gross = (o / c.shift(1) - 1).dropna()
id_gross = (c / o - 1).dropna()
recon = (1 + on_gross) * (1 + id_gross.reindex(on_gross.index)) - 1
cc = c.pct_change().reindex(on_gross.index)
err = (recon - cc).abs().median()
print(f"[sanity] median |overnight*intraday - cc| = {err:.2e}  (should be ~0)")
print(f"[sanity] SPY mean daily: cc={cc.mean()*1e4:.2f}bp  overnight={on_gross.mean()*1e4:.2f}bp  intraday={id_gross.mean()*1e4:.2f}bp")

# B1: QQQ buy & hold
results.append(stats(close("qqq.us").pct_change().dropna(), bench, "B1 QQQ buy&hold"))

# H1a: SPY > MA200
ma200 = c.rolling(200).mean()
pos = (c > ma200).astype(float)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H1a MA200 timing"))

# H1b: 12m time-series momentum
pos = (c > c.shift(252)).astype(float)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H1b TSMOM 12m"))

# H2a/b: overnight only / intraday only (2 sides per day)
cst = cost_of("spy.us")
results.append(stats((on_gross - 2 * cst).dropna(), bench, "H2a Overnight only (net)"))
results.append(stats((id_gross - 2 * cst).dropna(), bench, "H2b Intraday only (net)"))

# H3: vol-managed (variance targeting, sigma_target=17% ann)
rv = bench.rolling(20).std() * np.sqrt(252)
raw = (0.17 ** 2 / rv ** 2)
pos_a = raw.clip(0, 1).reindex(c.index)
pos_b = raw.clip(0, 2).reindex(c.index)
pos_a = (pos_a * 10).round() / 10
pos_b = (pos_b * 10).round() / 10
results.append(stats(single_asset_strategy(pos_a.fillna(0), c, cash, sym="spy.us"), bench, "H3a Vol-managed [0,1]"))
results.append(stats(single_asset_strategy(pos_b.fillna(0), c, cash, sym="spy.us"), bench, "H3b Vol-managed [0,2]"))

# H4: turn-of-month (last 4 + first 3 trading days); calendar known ex-ante,
# so anticipate by one day (single_asset_strategy lags pos by 1)
tom = turn_of_month_mask(c.index).astype(float).shift(-1).fillna(0.0)
results.append(stats(single_asset_strategy(tom, c, cash, sym="spy.us"), bench, "H4 Turn-of-month"))

# H5: RSI(2) mean reversion, trend-filtered (Connors)
r2 = rsi(c, 2)
ma5 = c.rolling(5).mean()
enter = ((r2 < 10) & (c > ma200)).values
exit_ = (c > ma5).values
state = np.zeros(len(c))
holding = False
for i in range(len(c)):
    if holding and exit_[i]:
        holding = False
    elif not holding and enter[i]:
        holding = True
    state[i] = 1.0 if holding else 0.0
pos = pd.Series(state, index=c.index)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H5 RSI(2) dip-buy"))

# H6: sector momentum — top 3 of 9 SPDRs by 12-1 momentum, monthly
secs = ["xlk.us", "xlf.us", "xle.us", "xlv.us", "xli.us", "xlp.us", "xlu.us", "xly.us", "xlb.us"]
C = pd.concat([close(s) for s in secs], axis=1).dropna()
mom = C.shift(21) / C.shift(252) - 1
me = month_end_mask(C.index)
W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
ranks = mom[me].rank(axis=1, ascending=False)
w_me = (ranks <= 3).astype(float) / 3.0
W[me] = w_me
W[~me] = np.nan
W = W.ffill().fillna(0.0)
results.append(stats(multi_asset_strategy(W, C, cash), bench, "H6 Sector mom top3"))

# H7: dual momentum SPY/EFA/AGG monthly
duo = pd.concat([close("spy.us"), close("efa.us"), close("agg.us"), close("shy.us")], axis=1).dropna()
duo.columns = ["spy", "efa", "agg", "shy"]
m12 = duo / duo.shift(252) - 1
me = month_end_mask(duo.index)
W = pd.DataFrame(0.0, index=duo.index, columns=["spy", "efa", "agg"])
sel = pd.DataFrame(index=duo.index[me], columns=W.columns, data=0.0)
m = m12[me]
risk_on = m[["spy", "efa"]].max(axis=1) > m["shy"]
pick_spy = (m["spy"] >= m["efa"]) & risk_on
pick_efa = (m["efa"] > m["spy"]) & risk_on
sel.loc[pick_spy.values, "spy"] = 1.0
sel.loc[pick_efa.values, "efa"] = 1.0
sel.loc[(~risk_on).values, "agg"] = 1.0
W[me] = sel.values
W[~me] = np.nan
W = W.ffill().fillna(0.0)
CC = duo[["spy", "efa", "agg"]].copy()
CC.columns = ["spy.us", "efa.us", "agg.us"]
W.columns = ["spy.us", "efa.us", "agg.us"]
results.append(stats(multi_asset_strategy(W, CC, cash), bench, "H7 Dual momentum"))

# H8/H9: factor ETF buy & hold
for sym, nm in [("splv.us", "H8 SPLV low-vol B&H"), ("mtum.us", "H9 MTUM momentum B&H"),
                ("qual.us", "H9b QUAL quality B&H"), ("usmv.us", "H8b USMV min-vol B&H")]:
    try:
        results.append(stats(close(sym).pct_change().dropna(), bench, nm))
    except Exception as e:
        print(f"[skip] {nm}: {e}")

# H10: SSO (2x) when SPY>MA200 else cash
sso = close("sso.us")
pos = (c > ma200).astype(float).reindex(sso.index).fillna(0.0)
results.append(stats(single_asset_strategy(pos, sso, cash, sym="sso.us"), bench, "H10 SSO + MA200"))

# H12: SSO during turn-of-month else cash
pos = turn_of_month_mask(sso.index).astype(float).shift(-1).fillna(0.0)
results.append(stats(single_asset_strategy(pos, sso, cash, sym="sso.us"), bench, "H12 SSO turn-of-month"))

# H13: VIX filter — SPY only when VIX < 25
vix = None
for v in ["vix", "vix.us"]:
    try:
        vix = close(v)
        break
    except Exception:
        continue
if vix is not None:
    pos = (vix < 25).astype(float).reindex(c.index).ffill().fillna(0.0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H13 VIX<25 filter"))
else:
    print("[skip] H13: no VIX data")

print()
print(fmt_table(results))
pd.DataFrame(results).to_csv("round1_results.csv", index=False)
print("\nsaved round1_results.csv")
