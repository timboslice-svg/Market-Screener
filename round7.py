"""Round 7: creative structural hypotheses — lead-lag, correlation regimes,
calendar structure mined from the data itself, CTA overlay stacking.
Run: python3 round7.py"""
import numpy as np
import pandas as pd
from harness import (load, close, single_asset_strategy, multi_asset_strategy,
                     stats, fmt_table, month_end_mask)

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
ma200 = c.rolling(200).mean()


def maybe(sym):
    try:
        return close(sym)
    except Exception:
        return None


# H50 GTAA: SPY/TLT/GLD/VNQ/EFA/EEM, top-2 by 126d momentum, monthly
univ = {}
for s in ["spy.us", "tlt.us", "gld.us", "vnq.us", "efa.us", "eem.us"]:
    ser = maybe(s)
    if ser is not None:
        univ[s] = ser
if len(univ) >= 5:
    C = pd.concat(univ.values(), axis=1)
    C.columns = list(univ.keys())
    C = C.dropna()
    mom = C / C.shift(126) - 1
    me = month_end_mask(C.index)
    ranks = mom[me].rank(axis=1, ascending=False)
    W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    W[me] = (ranks <= 2).astype(float) / 2.0
    W[~me] = np.nan
    W = W.ffill().fillna(0.0)
    results.append(stats(multi_asset_strategy(W, C, cash), bench, "H50 GTAA6 top2"))

# H51 Pre-holiday days (gap to next trading day > 3 calendar days => long weekend/holiday);
# overlay: 2x on pre-holiday + pre-weekend-holiday days via SSO, else SPY
dates = pd.Series(c.index, index=c.index)
gap_days = (dates.shift(-1) - dates).dt.days
dow = dates.dt.dayofweek
# normal gaps: weekday->next day = 1, Friday->Monday = 3. Anything larger implies a holiday.
prehol_any = ((dow < 4) & (gap_days >= 2)) | ((dow == 4) & (gap_days > 3))
print(f"[H51] pre-holiday days/yr: {prehol_any.mean() * 252:.1f}")
# calendar known ex-ante: anticipate by one day (strategy lags pos by 1)
pos = pd.Series(np.where(prehol_any, 1.0, 0.0), index=c.index).shift(-1).fillna(0.0)
results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H51 Pre-holiday only"))

# H52 Defensive-ratio composite: cash only when XLP beats XLY (63d) AND SPY<MA200
xlp, xly = maybe("xlp.us"), maybe("xly.us")
if xlp is not None and xly is not None:
    idx = c.index.intersection(xlp.index).intersection(xly.index)
    defsig = ((xlp / xlp.shift(63) - 1) > (xly / xly.shift(63) - 1)).reindex(idx)
    below = (c < ma200).reindex(idx)
    riskoff = (defsig & below).astype(float)
    pos = (1.0 - riskoff).fillna(1.0)
    results.append(stats(single_asset_strategy(pos, c.reindex(idx), cash, sym="spy.us"), bench, "H52 Defensive-ratio gate"))

# H53 Semis lead: hold QQQ when SMH 63d momentum > 0, else cash
smh = maybe("smh.us")
q = maybe("qqq.us")
if smh is not None and q is not None:
    idx = q.index.intersection(smh.index)
    sig = (smh / smh.shift(63) - 1).reindex(idx) > 0
    pos = sig.astype(float)
    results.append(stats(single_asset_strategy(pos, q.reindex(idx), cash, sym="qqq.us"), bench, "H53 SMH-lead QQQ"))

# H54 Dow-theory veto: cash only when BOTH SPY<MA200 and IYT<its MA200
iyt = maybe("iyt.us")
if iyt is not None:
    idx = c.index.intersection(iyt.index)
    veto = ((c < ma200).reindex(idx) & (iyt < iyt.rolling(200).mean()).reindex(idx))
    pos = (1.0 - veto.astype(float)).fillna(1.0)
    results.append(stats(single_asset_strategy(pos, c.reindex(idx), cash, sym="spy.us"), bench, "H54 Dow-theory veto"))

# H55 Sector-correlation regime: derisk when avg pairwise 63d correlation is in top expanding quintile
secs = ["xlk.us", "xlf.us", "xle.us", "xlv.us", "xli.us", "xlp.us", "xlu.us", "xly.us", "xlb.us"]
try:
    CS = pd.concat([close(s) for s in secs], axis=1).dropna()
    RS = CS.pct_change()
    corr = RS.rolling(63).corr()
    # mean off-diagonal correlation per date
    n = len(secs)
    avgc = corr.groupby(level=0).apply(lambda m: (m.values.sum() - np.trace(m.values)) / (n * n - n))
    avgc.index = avgc.index.get_level_values(0) if isinstance(avgc.index, pd.MultiIndex) else avgc.index
    pctl = avgc.expanding(252).apply(lambda x: (x.iloc[-1] > x).mean(), raw=False)
    pos = pd.Series(np.where(pctl > 0.8, 0.5, 1.0), index=avgc.index).reindex(c.index).ffill().fillna(1.0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H55 Corr-regime derisk"))
except Exception as e:
    print(f"[skip H55] {e}")

# H56 VIX term-slope equity timing: cash when backwardation (VIX3M<VIX)
vix = maybe("vix")
if vix is None:
    vix = maybe("vix.us")
vix3m = maybe("vix3m")
if vix is not None and vix3m is not None:
    slope = (vix3m / vix).dropna()
    pos = (slope >= 1.0).astype(float).reindex(c.index).ffill().fillna(1.0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, "H56 Contango-only SPY"))

# H57 CTA-stack: 1.0 SPY + 0.5 split across 12m-trend longs in {bonds, gold, dollar} futures
futs = {}
for s, nm in [("zn.f", "zn"), ("ty.f", "ty"), ("gc.f", "gc"), ("dx.f", "dx")]:
    ser = maybe(s)
    if ser is not None and len(ser) > 1000:
        futs[nm] = ser
if "zn" in futs and "ty" in futs:
    futs.pop("ty")  # same contract under two symbols; keep one
if len(futs) >= 2:
    F = pd.concat(futs.values(), axis=1)
    F.columns = list(futs.keys())
    idx = c.index.intersection(F.index)
    F = F.reindex(idx)
    sig = (F > F.shift(252)).astype(float)
    k = len(F.columns)
    w_f = sig * (0.5 / k)
    W = pd.concat([pd.Series(1.0, index=idx, name="spy.us"), w_f], axis=1)
    A = pd.concat([c.reindex(idx), F], axis=1)
    A.columns = ["spy.us"] + list(F.columns)
    rf = A.pct_change()
    bad = rf.abs() > 0.5
    if bad.any().any():
        print(f"[H57] clipped {int(bad.sum().sum())} absurd futures returns (roll artifacts)")
        A = A.where(~bad.shift(-1).fillna(False))  # crude guard
    costs = {col: (1e-4 if col == "spy.us" else 1.5e-4) for col in A.columns}
    results.append(stats(multi_asset_strategy(W, A, cash, costs=costs), bench, "H57 SPY + CTA overlay"))
else:
    print("[skip H57] insufficient futures data")

# H58 Gap-conditional intraday (diagnostic): fade opens >+0.3%, follow opens <-0.3%
gap = (o / c.shift(1) - 1)
intraday = (c / o - 1)
fade = np.where(gap > 0.003, -intraday, np.where(gap < -0.003, intraday, 0.0))
n_sig = (np.abs(gap) > 0.003).sum()
tc = 2e-4 * (np.abs(gap) > 0.003)
sr = pd.Series(fade, index=c.index) - tc
results.append(stats(sr.dropna(), bench, "H58 Gap fade/follow"))

# H59 SPY/QQQ/IWM rotation by 126d vol-adjusted momentum, AGG fallback
trio = {}
for s in ["spy.us", "qqq.us", "iwm.us", "agg.us"]:
    ser = maybe(s)
    if ser is not None:
        trio[s] = ser
if len(trio) == 4:
    C = pd.concat(trio.values(), axis=1)
    C.columns = list(trio.keys())
    C = C.dropna()
    R = C.pct_change()
    mom = (C / C.shift(126) - 1) / (R.rolling(126).std() * np.sqrt(252))
    me = month_end_mask(C.index)
    eq = mom[["spy.us", "qqq.us", "iwm.us"]]
    eq_me = eq[me].dropna(how="all")
    best = eq_me.idxmax(axis=1)
    use_agg = eq_me.max(axis=1) < 0
    wm = pd.DataFrame(0.0, index=eq_me.index, columns=C.columns)
    for col in ["spy.us", "qqq.us", "iwm.us"]:
        wm.loc[(best == col) & (~use_agg), col] = 1.0
    wm.loc[use_agg, "agg.us"] = 1.0
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    W.loc[wm.index] = wm
    W = W.ffill().fillna(0.0)
    results.append(stats(multi_asset_strategy(W, C, cash), bench, "H59 Index rotation"))

print(fmt_table(results))
pd.DataFrame(results).to_csv("round7_results.csv", index=False)
print("saved round7_results.csv")
