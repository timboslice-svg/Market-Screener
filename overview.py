"""Market overview: index/asset moves + universe breadth -> overview.json.
Run after scan.py (uses prices_cache.csv)."""
import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

ASSETS = [
    ("^GSPC", "S&P 500"), ("^NDX", "Nasdaq 100"), ("^GDAXI", "DAX"),
    ("^FTSE", "FTSE 100"), ("^FCHI", "CAC 40"), ("^N225", "Nikkei 225"),
    ("^AXJO", "ASX 200"), ("^STI", "STI"), ("^VIX", "VIX"),
    ("^TNX", "US 10y yield"), ("EURUSD=X", "EUR/USD"), ("GC=F", "Gold"),
    ("CL=F", "WTI Crude"), ("BTC-USD", "Bitcoin"),
]


def main():
    px = pd.read_csv(os.path.join(HERE, "prices_cache.csv"), index_col=0, parse_dates=True)
    uni = pd.read_csv(os.path.join(HERE, "universe.csv"))
    markets = []
    for tick, label in ASSETS:
        if tick not in px.columns:
            continue
        c = px[tick].dropna()
        if len(c) < 30:
            continue
        lvl = float(c.iloc[-1])
        r1 = c.iloc[-1] / c.iloc[-2] - 1
        r5 = c.iloc[-1] / c.iloc[-6] - 1 if len(c) > 6 else None
        r21 = c.iloc[-1] / c.iloc[-22] - 1 if len(c) > 22 else None
        markets.append({"name": label, "level": round(lvl, 2),
                        "r1": round(r1 * 100, 2),
                        "r5": round(r5 * 100, 2) if r5 is not None else None,
                        "r21": round(r21 * 100, 2) if r21 is not None else None})
    stocks = [t for t in uni["ticker"] if t in px.columns]
    S = px[stocks].dropna(axis=1, thresh=60)
    r1 = S.iloc[-1] / S.iloc[-2] - 1
    ma50 = S.rolling(50).mean().iloc[-1]
    breadth = {
        "n_stocks": int(S.shape[1]),
        "pct_up_1d": round(float((r1 > 0).mean()) * 100, 1),
        "pct_above_50dma": round(float((S.iloc[-1] > ma50).mean()) * 100, 1),
        "median_1d": round(float(r1.median()) * 100, 2),
    }
    try:
        with open(os.path.join(HERE, "flags.json")) as fh:
            flags = json.load(fh)
        breadth["flags_up"] = sum(1 for f in flags if f["side"] == "up")
        breadth["flags_down"] = sum(1 for f in flags if f["side"] == "down")
    except Exception:
        pass
    out = {"markets": markets, "breadth": breadth, "ai_note": ""}
    old = os.path.join(HERE, "overview.json")
    if os.path.exists(old):  # preserve an ai_note written by the triage step
        try:
            with open(old) as fh:
                prev = json.load(fh)
            if prev.get("ai_note"):
                out["ai_note"] = prev["ai_note"]
        except Exception:
            pass
    with open(os.path.join(HERE, "overview.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"overview: {len(markets)} assets, breadth over {breadth['n_stocks']} stocks "
          f"({breadth['pct_up_1d']}% up, {breadth['pct_above_50dma']}% above 50dma)")


if __name__ == "__main__":
    main()
