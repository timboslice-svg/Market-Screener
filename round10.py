"""Round 10: leverage controls + placebo for the calendar overlays, era splits,
armored variants, and the SPY-implementable version. Run: python3 round10.py"""
import os
import numpy as np
import pandas as pd
from harness import (load, close, stats, fmt_table, month_end_mask,
                     turn_of_month_mask, DATA)

results = []


def load_ff(name):
    df = pd.read_csv(os.path.join(DATA, name), parse_dates=["Date"]).set_index("Date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce") / 100.0


fac = load_ff("ff_factors.csv")
mkt = (fac["MktRF"] + fac["RF"]).rename("mkt").dropna()
rf = fac["RF"].reindex(mkt.index).fillna(0.0)
FIN = rf + 0.005 / 252
mkt_idx = (1 + mkt).cumprod()
ma200 = mkt_idx.rolling(200).mean()

tom = turn_of_month_mask(mkt.index).astype(float)
dates = pd.Series(mkt.index, index=mkt.index)
gap_days = (dates.shift(-1) - dates).dt.days
dow = dates.dt.dayofweek
prehol = (((dow < 4) & (gap_days >= 2)) | ((dow == 4) & (gap_days > 3))).astype(float).fillna(0.0)

# mid-month placebo window with ~the same day count as TOM (7 trading days)
per = mkt.index.to_period("M")
g = pd.Series(np.arange(len(mkt.index)), index=mkt.index)
from_start = g.groupby(per).cumcount() + 1
placebo = ((from_start >= 8) & (from_start <= 14)).astype(float)

print(f"[exposure] TOM frac={tom.mean():.3f} prehol frac={prehol.mean():.3f} placebo frac={placebo.mean():.3f}")

ERAS = [("1927-2026", None, None), ("1927-1963", "1927", "1963"),
        ("1963-1993", "1963", "1993"), ("1993-2010", "1993", "2010"),
        ("2010-2026", "2010", None)]


def era_stats(sr, name, eras=ERAS):
    for era, a, b in eras:
        s = sr.loc[a:b] if a or b else sr
        results.append(stats(s, mkt, f"{name} {era}"))


def overlay(mask):
    return (mkt + mask * (mkt - FIN) - 1e-4 * mask.diff().abs()).dropna()


# --- 1. CONTROLS: constant leverage matched to average exposure
for lev, nm in [(1.0 + tom.mean(), "ctrl const-lev (TOM avg)"),
                (1.0 + prehol.mean(), "ctrl const-lev (ph avg)"),
                (1.0 + tom.mean() + prehol.mean(), "ctrl const-lev (both)")]:
    sr = (lev * mkt - (lev - 1) * FIN).dropna()
    results.append(stats(sr, mkt, nm))

# --- 2. PLACEBO overlay (mid-month days)
results.append(stats(overlay(placebo), mkt, "PLACEBO mid-month ovl"))

# --- 3. Era splits for the overlays
era_stats(overlay(tom), "TOM ovl")
era_stats(overlay(prehol), "Prehol ovl")
era_stats(overlay(tom) if False else (mkt + (tom + prehol) * (mkt - FIN)
          - 1e-4 * (tom.diff().abs() + prehol.diff().abs())).dropna(), "TOM+ph ovl")

# --- 4. Armored overlay: extra exposure only when mkt above MA200
armor = (mkt_idx > ma200).astype(float).shift(1).fillna(0.0)
sr = (mkt + tom * armor * (mkt - FIN) - 1e-4 * (tom * armor).diff().abs()).dropna()
era_stats(sr, "TOM ovl+trend armor", eras=[("1927-2026", None, None), ("2010-2026", "2010", None)])

# --- 5. MOM-factor overlay era splits
try:
    momf = load_ff("ff_mom.csv").iloc[:, 0].dropna()
    sr = (mkt + 0.3 * momf.reindex(mkt.index).fillna(0.0) - 0.3 * 0.02 / 252).dropna()
    era_stats(sr, "0.3 MOM ovl")
except Exception as e:
    print(f"[skip mom ovl eras] {e}")

# --- 6. IndMom best variants, era splits
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


im8 = industry_mom(8)
era_stats(im8, "IndMom k=8", eras=[("1927-2026", None, None), ("1993-2010", "1993", "2010"), ("2010-2026", "2010", None)])
im5 = industry_mom(5)
gate_im = (mkt_idx > ma200).astype(float).shift(1).reindex(im5.index).fillna(1.0)
sr = (gate_im * im5 + (1 - gate_im) * rf.reindex(im5.index).fillna(0.0)).dropna()
era_stats(sr, "IndMom+gate", eras=[("1927-2026", None, None), ("1993-2010", "1993", "2010"), ("2010-2026", "2010", None)])

# --- 7. SPY-implementable TOM overlay (real ETF data, real financing), 1993+ / 2010+
try:
    spy = close("spy.us")
    spyr = spy.pct_change().dropna()
    try:
        shy = close("shy.us").pct_change().reindex(spyr.index).fillna(0.0)
    except Exception:
        shy = pd.Series(0.0, index=spyr.index)
    fin = shy + 0.005 / 252
    tom_e = turn_of_month_mask(spyr.index).astype(float)
    sr = (spyr + tom_e * (spyr - fin) - 1e-4 * tom_e.diff().abs()).dropna()
    results.append(stats(sr, spyr, "SPY + TOM ovl 1993+"))
    results.append(stats(sr.loc["2010":], spyr, "SPY + TOM ovl 2010+"))
    results.append(stats(sr.loc["2015":], spyr, "SPY + TOM ovl 2015+"))
    # placebo on SPY era too
    per_e = spyr.index.to_period("M")
    ge = pd.Series(np.arange(len(spyr.index)), index=spyr.index)
    fs = ge.groupby(per_e).cumcount() + 1
    plc = ((fs >= 8) & (fs <= 14)).astype(float)
    sr_p = (spyr + plc * (spyr - fin) - 1e-4 * plc.diff().abs()).dropna()
    results.append(stats(sr_p, spyr, "SPY + placebo ovl 1993+"))
except Exception as e:
    print(f"[skip SPY overlays] {e}")

print(fmt_table(results))
pd.DataFrame(results).to_csv("round10_results.csv", index=False)
print("saved round10_results.csv")
