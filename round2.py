"""Round 2: robustness sweeps for round-1 survivors.
Edit SWEEPS to match what survived; default covers the likely candidates.
Run: python3 round2.py
"""
import numpy as np
import pandas as pd
from harness import (load, close, single_asset_strategy, multi_asset_strategy,
                     stats, fmt_table, month_end_mask, turn_of_month_mask, cost_of)

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


def subperiod_report(sr, bench, name, block_years=5):
    """Excess return by calendar block — stability check."""
    df = pd.concat([sr.rename("s"), bench.rename("b")], axis=1, join="inner").dropna()
    out = [name]
    y0 = df.index[0].year
    while y0 <= df.index[-1].year:
        blk = df[(df.index.year >= y0) & (df.index.year < y0 + block_years)]
        if len(blk) > 60:
            ex = (1 + blk["s"]).prod() / (1 + blk["b"]).prod() - 1
            out.append(f"  {y0}-{min(y0+block_years-1, df.index[-1].year)}: {ex*+100:+.1f}%")
        y0 += block_years
    return "\n".join(out)


subreports = []

# --- Family: trend timing (if H1/H10 survived) ---
for L in [100, 150, 200, 250, 300]:
    ma = c.rolling(L).mean()
    pos = (c > ma).astype(float)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, f"MA{L} timing SPY"))
try:
    sso = close("sso.us")
    for L in [100, 150, 200, 250, 300]:
        ma = c.rolling(L).mean()
        pos = (c > ma).astype(float).reindex(sso.index).fillna(0.0)
        sr = single_asset_strategy(pos, sso, cash, sym="sso.us")
        results.append(stats(sr, bench, f"SSO + MA{L}"))
        if L == 200:
            subreports.append(subperiod_report(sr, bench, "SSO + MA200 by 5y block"))
except Exception as e:
    print(f"[skip sso sweep] {e}")

# --- Family: vol-managed ---
rv = bench.rolling(20).std() * np.sqrt(252)
for tgt in [0.13, 0.15, 0.17, 0.20]:
    for cap in [1.0, 1.5, 2.0]:
        pos = ((tgt ** 2) / rv ** 2).clip(0, cap).reindex(c.index)
        pos = ((pos * 10).round() / 10).fillna(0)
        sr = single_asset_strategy(pos, c, cash, sym="spy.us")
        results.append(stats(sr, bench, f"VolMgd t={tgt:.2f} cap={cap:.1f}"))
for win in [10, 20, 40, 60]:
    rvw = bench.rolling(win).std() * np.sqrt(252)
    pos = ((0.17 ** 2) / rvw ** 2).clip(0, 2).reindex(c.index)
    pos = ((pos * 10).round() / 10).fillna(0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, f"VolMgd win={win} cap=2"))

# --- Family: overnight ---
cst = cost_of("spy.us")
on_gross = (o / c.shift(1) - 1).dropna()
results.append(stats((on_gross - 2 * cst).dropna(), bench, "Overnight SPY (1bp/side)"))
results.append(stats((on_gross - 2 * 2.5e-4).dropna(), bench, "Overnight SPY (2.5bp/side)"))
try:
    q = load("qqq.us")
    onq = (q["Open"] / q["Close"].shift(1) - 1).dropna()
    results.append(stats((onq - 2 * cst).dropna(), bench, "Overnight QQQ (1bp/side)"))
    subreports.append(subperiod_report((onq - 2 * cst).dropna(), bench, "Overnight QQQ by 5y block"))
except Exception as e:
    print(f"[skip qqq overnight] {e}")

# --- Family: turn-of-month ---
for db, da in [(3, 2), (4, 3), (5, 4), (2, 1)]:
    pos = turn_of_month_mask(c.index, db, da).astype(float).shift(-1).fillna(0.0)
    results.append(stats(single_asset_strategy(pos, c, cash, sym="spy.us"), bench, f"TOM {db}+{da} SPY"))

# --- Family: sector momentum ---
secs = ["xlk.us", "xlf.us", "xle.us", "xlv.us", "xli.us", "xlp.us", "xlu.us", "xly.us", "xlb.us"]
try:
    C = pd.concat([close(s) for s in secs], axis=1).dropna()
    me = month_end_mask(C.index)
    for k in [2, 3, 4]:
        for skip in [21, 0]:
            mom = C.shift(skip) / C.shift(252) - 1
            W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
            ranks = mom[me].rank(axis=1, ascending=False)
            W[me] = (ranks <= k).astype(float) / k
            W[~me] = np.nan
            W = W.ffill().fillna(0.0)
            sr = multi_asset_strategy(W, C, cash)
            results.append(stats(sr, bench, f"SectorMom top{k} skip{skip}"))
except Exception as e:
    print(f"[skip sector sweep] {e}")

print(fmt_table(results))
print()
for s in subreports:
    print(s)
    print()
pd.DataFrame(results).to_csv("round2_results.csv", index=False)
print("saved round2_results.csv")
