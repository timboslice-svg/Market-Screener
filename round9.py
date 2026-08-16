"""Round 9: robustness of the round-8 ACCEPTs + leverage overlays for RA-ONLYs.
All on French data (survivorship-free). Run: python3 round9.py"""
import os
import numpy as np
import pandas as pd
from harness import stats, fmt_table, month_end_mask, turn_of_month_mask, DATA

results = []


def load_ff(name):
    df = pd.read_csv(os.path.join(DATA, name), parse_dates=["Date"]).set_index("Date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce") / 100.0


fac = load_ff("ff_factors.csv")
mkt = (fac["MktRF"] + fac["RF"]).rename("mkt").dropna()
rf = fac["RF"].reindex(mkt.index).fillna(0.0)
mkt_idx = (1 + mkt).cumprod()
ma200 = mkt_idx.rolling(200).mean()

m10 = load_ff("ff_mom10.csv").replace(-0.9999, np.nan)
win = m10.iloc[:, -1].dropna()

ind = load_ff("ff_ind49.csv")
ind = ind.where(ind > -0.99)


def industry_mom(top_k=5, skip=21, form=252, cost_side=10e-4):
    cum = (1 + ind.fillna(0.0)).cumprod().where(ind.notna())
    mom = cum.shift(skip) / cum.shift(form) - 1
    me = month_end_mask(ind.index)
    ranks = mom[me].rank(axis=1, ascending=False)
    W = pd.DataFrame(0.0, index=ind.index, columns=ind.columns)
    W[me] = (ranks <= top_k).astype(float) / top_k
    W[~me] = np.nan
    W = W.ffill().fillna(0.0)
    held = W.shift(1).fillna(0.0)
    tc = cost_side * W.diff().abs().sum(axis=1)
    return ((held * ind.fillna(0.0)).sum(axis=1) - tc).dropna()


# --- 1. ERA ANALYSIS: is momentum alive post-publication / post-crowding?
ERAS = [("1927-2026", None, None), ("1927-1963", "1927", "1963"),
        ("1963-1993", "1963", "1993"), ("1993-2010", "1993", "2010"),
        ("2010-2026", "2010", None)]
DRAG = 0.015 / 252
im = industry_mom()
gate = (mkt_idx > ma200).astype(float).shift(1)
h65 = (gate * (win - DRAG) + (1 - gate) * rf).dropna()
for nm, sr in [("WinnerDecile", (win - DRAG).dropna()), ("IndustryMom", im), ("Win+TrendGate", h65)]:
    for era, a, b in ERAS:
        s = sr.loc[a:b] if a or b else sr
        results.append(stats(s, mkt, f"{nm} {era}"))

# --- 2. COST SENSITIVITY
for drag_ann in [0.0, 0.015, 0.03]:
    results.append(stats((win - drag_ann / 252).dropna(), mkt, f"Winners drag={drag_ann:.1%}/yr"))
for cs in [5e-4, 10e-4, 20e-4]:
    results.append(stats(industry_mom(cost_side=cs), mkt, f"IndMom cost={cs*1e4:.0f}bp/side"))

# --- 3. PARAMETER PERTURBATION (industry momentum)
for k in [3, 5, 8]:
    for skip, form in [(21, 252), (0, 252), (21, 126)]:
        if k == 5 and skip == 21 and form == 252:
            continue
        results.append(stats(industry_mom(k, skip, form), mkt, f"IndMom k={k} s={skip} f={form}"))

# --- 4. CRASH ARMOR: vol-managed winner decile (Barroso/Santa-Clara style)
rv = win.rolling(126).std() * np.sqrt(252)
scale = (0.20 / rv).clip(0, 1.5)
sr = (scale.shift(1) * (win - DRAG) + (1 - scale.shift(1)).clip(lower=0) * rf
      - (scale.shift(1) - 1).clip(lower=0) * (rf + 0.005 / 252)).dropna()
results.append(stats(sr, mkt, "Winners vol-managed"))

# --- 5. RA-ONLY exploitation: calendar leverage overlays (extra exposure via futures)
FIN = rf + 0.005 / 252
tom = turn_of_month_mask(mkt.index).astype(float)
sr = (mkt + tom * (mkt - FIN) - 1e-4 * tom.diff().abs()).dropna()
results.append(stats(sr, mkt, "Mkt + 1x TOM overlay"))
dates = pd.Series(mkt.index, index=mkt.index)
gap_days = (dates.shift(-1) - dates).dt.days
dow = dates.dt.dayofweek
prehol = (((dow < 4) & (gap_days >= 2)) | ((dow == 4) & (gap_days > 3))).astype(float).fillna(0.0)
sr = (mkt + prehol * (mkt - FIN) - 1e-4 * prehol.diff().abs()).dropna()
results.append(stats(sr, mkt, "Mkt + 1x pre-holiday ovl"))
sr = (mkt + tom * (mkt - FIN) + prehol * (mkt - FIN)
      - 1e-4 * (tom.diff().abs() + prehol.diff().abs())).dropna()
results.append(stats(sr, mkt, "Mkt + TOM + prehol ovl"))

# --- 6. Combined candidate: industry momentum + trend-gate to cash
gate_im = (mkt_idx > ma200).astype(float).shift(1).reindex(im.index).fillna(1.0)
sr = (gate_im * im + (1 - gate_im) * rf.reindex(im.index).fillna(0.0)).dropna()
results.append(stats(sr, mkt, "IndMom + trend gate"))

# --- 7. Momentum factor overlay (fixed H66: first numeric column)
try:
    momf = load_ff("ff_mom.csv").iloc[:, 0].dropna()
    sr = (mkt + 0.3 * momf.reindex(mkt.index).fillna(0.0) - 0.3 * 0.02 / 252).dropna()
    results.append(stats(sr, mkt, "Mkt + 0.3 MOM overlay"))
except Exception as e:
    print(f"[skip mom overlay] {e}")

print(fmt_table(results))
pd.DataFrame(results).to_csv("round9_results.csv", index=False)
print("saved round9_results.csv")
