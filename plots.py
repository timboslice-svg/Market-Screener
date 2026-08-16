"""Equity curves (log scale) for selected strategies vs SPY. Saves curves.png.
Usage: python3 plots.py   (edit STRATS below after seeing results)"""
import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as e:
    raise SystemExit(f"matplotlib unavailable: {e}")

from harness import load, close, single_asset_strategy

spy = load("spy.us")
c = spy["Close"]
bench = c.pct_change().dropna()

def curve(r):
    return (1 + r).cumprod()

series = {"SPY total return": curve(bench)}

# Rebuild the headline strategies inline (kept in sync with round scripts)
shy = close("shy.us").pct_change().reindex(c.index).fillna(0.0)
ma200 = c.rolling(200).mean()

try:
    sso = close("sso.us")
    pos = (c > ma200).astype(float).reindex(sso.index).fillna(0.0)
    series["SSO + MA200"] = curve(single_asset_strategy(pos, sso, shy, sym="sso.us"))
except Exception:
    pass
try:
    q = close("qqq.us")
    series["QQQ B&H"] = curve(q.pct_change().dropna())
    qma = q.rolling(200).mean()
    series["QQQ + MA200"] = curve(single_asset_strategy((q > qma).astype(float), q, shy, sym="qqq.us"))
except Exception:
    pass

fig, ax = plt.subplots(figsize=(12, 7))
for name, cur in series.items():
    ax.plot(cur.index, cur.values, label=name, linewidth=1.2)
ax.set_yscale("log")
ax.legend()
ax.set_title("Equity curves (net of costs), log scale")
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("curves.png", dpi=130)
print("saved curves.png")
