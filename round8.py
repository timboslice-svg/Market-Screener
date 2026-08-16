"""Round 8: century-scale, survivorship-FREE tests on Ken French data (1926+).
Benchmark inside this round = total US market return (MktRF+RF), not SPY —
noted in the report. Portfolio strategies get an implementability haircut.
Run: python3 round8.py
"""
import os
import numpy as np
import pandas as pd
from harness import stats, fmt_table, month_end_mask, turn_of_month_mask, DATA

results = []


def load_ff(name):
    df = pd.read_csv(os.path.join(DATA, name), parse_dates=["Date"]).set_index("Date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce") / 100.0  # percent -> decimal


try:
    fac = load_ff("ff_factors.csv")
except Exception as e:
    raise SystemExit(f"[round8] no ff_factors.csv: {e}")
mkt = (fac["MktRF"] + fac["RF"]).rename("mkt").dropna()
rf = fac["RF"].reindex(mkt.index).fillna(0.0)
mkt_idx = (1 + mkt).cumprod()

# H60 Winner decile (12-2 momentum, decile 10) B&H with 1.5%/yr implementation drag
try:
    m10 = load_ff("ff_mom10.csv")
    m10 = m10.replace(-0.9999, np.nan)
    win = m10.iloc[:, -1].dropna()  # highest-prior-return decile
    lose = m10.iloc[:, 0].dropna()
    DRAG = 0.015 / 252
    results.append(stats((win - DRAG).dropna(), mkt, "H60 Winner decile (net)"))
    results.append(stats((lose).dropna(), mkt, "H60b Loser decile (gross)"))
    # H65 winner decile with market-trend gate (hold winners only when mkt>MA200, else RF)
    ma200 = mkt_idx.rolling(200).mean()
    gate = (mkt_idx > ma200).astype(float).shift(1)
    sr = (gate * (win - DRAG) + (1 - gate) * rf).dropna()
    results.append(stats(sr, mkt, "H65 Winners + trend gate"))
except Exception as e:
    print(f"[skip H60/H65] {e}")

# H61 Trend timing on the market, 1926-2026 (the definitive sample)
ma200 = mkt_idx.rolling(200).mean()
pos = (mkt_idx > ma200).astype(float).shift(1)
sr = (pos * mkt + (1 - pos) * rf - 1e-4 * pos.diff().abs()).dropna()
results.append(stats(sr, mkt, "H61 Mkt MA200 1926+"))

# H63 Turn-of-month on the market, 1926+ (calendar known ex-ante: no signal lag)
tom = turn_of_month_mask(mkt.index).astype(float)
sr = (tom * mkt + (1 - tom) * rf - 1e-4 * tom.diff().abs()).dropna()
results.append(stats(sr, mkt, "H63 TOM 1926+"))

# H64 Pre-holiday on the market, 1926+
dates = pd.Series(mkt.index, index=mkt.index)
gap_days = (dates.shift(-1) - dates).dt.days
dow = dates.dt.dayofweek
prehol = (((dow < 4) & (gap_days >= 2)) | ((dow == 4) & (gap_days > 3))).astype(float).fillna(0.0)
sr = (prehol * mkt + (1 - prehol) * rf - 1e-4 * prehol.diff().abs()).dropna()
results.append(stats(sr, mkt, "H64 Pre-holiday 1926+"))

# H62 Industry momentum: top 5 of 49 by 12-1, monthly, 10bp/side haircut on turnover
try:
    ind = load_ff("ff_ind49.csv")
    ind = ind.where(ind > -0.99)  # -99.99 = missing
    cum = (1 + ind.fillna(0.0)).cumprod().where(ind.notna())
    mom = cum.shift(21) / cum.shift(252) - 1
    me = month_end_mask(ind.index)
    ranks = mom[me].rank(axis=1, ascending=False)
    W = pd.DataFrame(0.0, index=ind.index, columns=ind.columns)
    W[me] = (ranks <= 5).astype(float) / 5.0
    W[~me] = np.nan
    W = W.ffill().fillna(0.0)
    held = W.shift(1).fillna(0.0)
    tc = 10e-4 * W.diff().abs().sum(axis=1)
    sr = ((held * ind.fillna(0.0)).sum(axis=1) - tc).dropna()
    results.append(stats(sr, mkt, "H62 Industry mom top5"))
except Exception as e:
    print(f"[skip H62] {e}")

# H66 Momentum-factor overlay: market + 0.3x Mom long/short factor
try:
    momf = load_ff("ff_mom.csv")["Mom"].dropna()
    sr = (mkt + 0.3 * momf.reindex(mkt.index).fillna(0.0) - 0.30 * 0.02 / 252).dropna()
    results.append(stats(sr, mkt, "H66 Mkt + 0.3 MOM overlay"))
except Exception as e:
    print(f"[skip H66] {e}")

print(fmt_table(results))
pd.DataFrame(results).to_csv("round8_results.csv", index=False)
print("saved round8_results.csv")
print("NOTE: benchmark here = total US market (not SPY); French portfolios are")
print("cost-free academic constructs — drags applied are estimates.")
