"""Round 12: TOM-overlay deep dive — decade stability, intensity/window sweeps,
international replication, micro-futures sizing. Run: python3 round12.py"""
import os
import numpy as np
import pandas as pd
from harness import close, stats, fmt_table, turn_of_month_mask, DATA

results = []


def load_ff(name):
    df = pd.read_csv(os.path.join(DATA, name), parse_dates=["Date"]).set_index("Date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce") / 100.0


fac = load_ff("ff_factors.csv")
mkt = (fac["MktRF"] + fac["RF"]).rename("mkt").dropna()
rf = fac["RF"].reindex(mkt.index).fillna(0.0)
FIN = rf + 0.005 / 252


def overlay(ret, fin, mask, mult=1.0):
    return (ret + mult * mask * (ret - fin) - 1e-4 * mult * mask.diff().abs()).dropna()


tom = turn_of_month_mask(mkt.index).astype(float)
base = overlay(mkt, FIN, tom)

# --- 1. Decade-by-decade stability
print("=" * 78)
print("TOM overlay (+1x on last4+first3 days) — excess vs market by decade")
print("=" * 78)
decades = [("1927-1939", "1927", "1939")] + [(f"{d}s", str(d), str(d + 9)) for d in range(1940, 2030, 10)]
for nm, a, b in decades:
    df = pd.concat([base.rename("s"), mkt.rename("b")], axis=1, join="inner").loc[a:b].dropna()
    if len(df) < 500:
        continue
    yrs = len(df) / 252
    ex = (1 + df["s"]).prod() ** (1 / yrs) - (1 + df["b"]).prod() ** (1 / yrs)
    d = df["s"] - df["b"]
    t = d.mean() / d.std() * np.sqrt(len(d))
    print(f"  {nm:<10} excess {ex*100:+5.1f}%/yr   t={t:+5.2f}   n={len(df)}")

# --- 2. Intensity sweep
for mult in [0.5, 1.0, 2.0]:
    sr = overlay(mkt, FIN, tom, mult)
    results.append(stats(sr, mkt, f"TOM ovl x{mult} century"))
    results.append(stats(sr.loc["2010":], mkt, f"TOM ovl x{mult} 2010+"))

# --- 3. Window sweep (century)
for db, da in [(4, 3), (3, 2), (5, 4), (2, 1)]:
    m = turn_of_month_mask(mkt.index, db, da).astype(float)
    results.append(stats(overlay(mkt, FIN, m), mkt, f"TOM ovl {db}+{da} century"))

# --- 4. International replication on ETFs (bench = the ETF itself)
print()
print("=" * 78)
print("International: overlay on each ETF vs that ETF buy&hold (real data, net)")
print("=" * 78)
try:
    shy = close("shy.us").pct_change()
except Exception:
    shy = None
for sym, nm in [("spy.us", "US S&P"), ("qqq.us", "US Nasdaq"), ("iwm.us", "US smallcap"),
                ("efa.us", "EAFE"), ("ewg.us", "Germany"), ("ewu.us", "UK"),
                ("ewj.us", "Japan"), ("ewa.us", "Australia"), ("ews.us", "Singapore"),
                ("eem.us", "EM")]:
    try:
        r = close(sym).pct_change().dropna()
    except Exception:
        continue
    fin = (shy.reindex(r.index).fillna(0.0) if shy is not None else pd.Series(0.0, index=r.index)) + 0.005 / 252
    m = turn_of_month_mask(r.index).astype(float)
    sr = overlay(r, fin, m)
    results.append(stats(sr, r, f"TOMovl {nm}"))

print(fmt_table(results))
pd.DataFrame(results).to_csv("round12_results.csv", index=False)

# --- 5. Micro-futures sizing (MES = $5 x S&P 500 index)
print()
print("=" * 78)
print("Implementation sizing: MES micro futures overlay (2 trades/month)")
print("=" * 78)
try:
    spx = close("spx").iloc[-1]
except Exception:
    spx = 6800.0
notional = 5 * spx
print(f"  S&P level {spx:.0f} -> MES notional ${notional:,.0f}")
print(f"  costs: ~0.5bp/side x 24 sides/yr = ~12bp/yr drag on overlay notional")
print(f"  financing: embedded in futures basis (~3m rate + ~0-50bp)")
print(f"  {'portfolio':>12} {'contracts':>10} {'overlay ratio':>14}")
for p in [25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]:
    k = round(p / notional)
    print(f"  {p:>12,} {k:>10d} {k*notional/p:>13.0%}")
print("  (contracts held only during the 7 TOM days; rest of month flat)")
print("saved round12_results.csv")
