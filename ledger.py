"""Recommendation ledger — the screener's self-evaluation. Appends today's flags,
fills forward 5/20-day excess returns for old flags, prints the running hit rate.
This is what tells us, months from now, whether the screener has any edge."""
import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ledger.csv")
COLS = ["date", "ticker", "region", "side", "z1", "z5", "price", "bench", "bench_px",
        "fwd5x", "fwd20x"]


def main():
    led = pd.read_csv(LEDGER) if os.path.exists(LEDGER) else pd.DataFrame(columns=COLS)
    with open(os.path.join(HERE, "flags.json")) as fh:
        flags = json.load(fh)

    # 1. append today's flags (idempotent on date+ticker)
    existing = set(zip(led["date"].astype(str), led["ticker"])) if len(led) else set()
    new_rows = [{k: f[k] for k in ["date", "ticker", "region", "side", "z1", "z5",
                                   "price", "bench", "bench_px"]}
                for f in flags if (f["date"], f["ticker"]) not in existing]
    if new_rows:
        led = pd.concat([led, pd.DataFrame(new_rows)], ignore_index=True)

    # 2. fill forward returns using the price cache
    px = pd.read_csv(os.path.join(HERE, "prices_cache.csv"), index_col=0, parse_dates=True)
    for i, row in led.iterrows():
        if pd.notna(row.get("fwd20x")):
            continue
        t, b = row["ticker"], row["bench"]
        if t not in px.columns or b not in px.columns:
            continue
        c = px[t].dropna()
        cb = px[b].dropna()
        d0 = pd.Timestamp(row["date"])
        after = c.index[c.index > d0]
        if len(after) == 0:
            continue
        e = after[0]  # entry = next close after flag
        pos = c.index.get_loc(e)
        posb = cb.index.get_loc(cb.index[cb.index >= e][0]) if (cb.index >= e).any() else None
        for h, col in [(5, "fwd5x"), (20, "fwd20x")]:
            if pd.notna(row.get(col)) or pos + h >= len(c) or posb is None or posb + h >= len(cb):
                continue
            fwd = c.iloc[pos + h] / c.iloc[pos] - 1
            fwdb = cb.iloc[posb + h] / cb.iloc[posb] - 1
            led.loc[i, col] = round((fwd - fwdb) * 100, 2)

    led.to_csv(LEDGER, index=False)

    res = led.dropna(subset=["fwd20x"])
    print(f"ledger: {len(led)} flags total, {len(res)} resolved at 20d")
    if len(res) >= 5:
        for side in ["down", "up"]:
            e = res[res["side"] == side]["fwd20x"]
            if len(e):
                print(f"  {side:<5} n={len(e):3d} mean 20d excess={e.mean():+.2f}% hit={(e > 0).mean()*100:.0f}%")


if __name__ == "__main__":
    main()
