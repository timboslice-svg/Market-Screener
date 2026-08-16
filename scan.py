"""Stage 1: nightly anomaly scan across the universe. Free data via yfinance.
Flags names whose move is unusual RELATIVE to their own volatility and their
regional index (idiosyncratic), or on abnormal volume. Writes flags.json +
prices_cache.csv. Run: python3 scan.py"""
import json
import os
import time
import numpy as np
import pandas as pd
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
uni = pd.read_csv(os.path.join(HERE, "universe.csv"))
BENCHES = sorted(uni["bench"].unique().tolist())
EXTRAS = ["^NDX", "^VIX", "^TNX", "EURUSD=X", "GC=F", "CL=F", "BTC-USD"]

Z1_FLAG = 2.5      # 1-day idiosyncratic z-score threshold
Z5_FLAG = 2.5      # 5-day
VOL_FLAG = 3.0     # volume ratio threshold (with |z1|>=1.5)
MAX_FLAGS = 40


def download(tickers, period="1y"):
    frames_c, frames_v = [], []
    for i in range(0, len(tickers), 25):
        chunk = tickers[i:i + 25]
        df = yf.download(chunk, period=period, interval="1d", auto_adjust=True,
                         progress=False, threads=False, group_by="column")
        if df is None or df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            frames_c.append(df["Close"])
            if "Volume" in df.columns.get_level_values(0):
                frames_v.append(df["Volume"])
        else:  # single ticker
            frames_c.append(df[["Close"]].rename(columns={"Close": chunk[0]}))
            frames_v.append(df[["Volume"]].rename(columns={"Volume": chunk[0]}))
        time.sleep(0.5)
    close = pd.concat(frames_c, axis=1, sort=True) if frames_c else pd.DataFrame()
    vol = pd.concat(frames_v, axis=1, sort=True) if frames_v else pd.DataFrame()
    return close, vol.sort_index() if not vol.empty else vol


def main():
    tickers = uni["ticker"].tolist()
    close, volume = download(tickers + BENCHES + EXTRAS)
    if close.empty:
        raise SystemExit("scan: no data downloaded")
    close = close.sort_index()
    r = close.pct_change()

    flags = []
    today = str(close.index[-1].date())
    for _, row in uni.iterrows():
        t, name, region, bench = row["ticker"], row["name"], row["region"], row["bench"]
        if t not in close.columns or bench not in close.columns:
            continue
        c = close[t].dropna()
        if len(c) < 120 or (close.index[-1] - c.index[-1]).days > 5:
            continue  # stale or too new
        idx = c.index
        rb = r[bench].reindex(idx).fillna(0.0)
        rt = r[t].reindex(idx)
        idio = (rt - rb).dropna()
        sigma = idio.tail(90).std()
        if not sigma or sigma <= 0:
            continue
        z1 = idio.iloc[-1] / sigma
        idio5 = (c.iloc[-1] / c.iloc[-6] - 1) - (close[bench].reindex(idx).ffill().iloc[-1]
                                                 / close[bench].reindex(idx).ffill().iloc[-6] - 1)
        z5 = idio5 / (sigma * np.sqrt(5))
        volratio = np.nan
        if t in volume.columns:
            v = volume[t].dropna()
            if len(v) > 25 and v.tail(21).iloc[:-1].mean() > 0:
                volratio = v.iloc[-1] / v.tail(21).iloc[:-1].mean()
        pct52 = c.iloc[-1] / c.tail(252).max()
        is_flag = (abs(z1) >= Z1_FLAG or abs(z5) >= Z5_FLAG
                   or (volratio and volratio >= VOL_FLAG and abs(z1) >= 1.5))
        if not is_flag:
            continue
        flags.append({
            "date": today, "ticker": t, "name": name, "region": region, "bench": bench,
            "r1": round(float(rt.iloc[-1]) * 100, 2), "z1": round(float(z1), 2),
            "r5": round(float(c.iloc[-1] / c.iloc[-6] - 1) * 100, 2), "z5": round(float(z5), 2),
            "volratio": round(float(volratio), 1) if volratio == volratio else None,
            "pct_52w_high": round(float(pct52) * 100, 1),
            "side": "down" if z1 + z5 < 0 else "up",
            "price": round(float(c.iloc[-1]), 2),
            "bench_px": round(float(close[bench].dropna().iloc[-1]), 2),
        })

    flags.sort(key=lambda f: -(abs(f["z1"]) + abs(f["z5"])))
    flags = flags[:MAX_FLAGS]
    with open(os.path.join(HERE, "flags.json"), "w") as fh:
        json.dump(flags, fh, indent=1)
    close.to_csv(os.path.join(HERE, "prices_cache.csv"))
    print(f"scan: {len(flags)} flags on {today} "
          f"({sum(1 for f in flags if f['side'] == 'down')} down / "
          f"{sum(1 for f in flags if f['side'] == 'up')} up)")
    for f in flags[:12]:
        print(f"  {f['ticker']:<10} {f['region']:<3} z1={f['z1']:+5.1f} z5={f['z5']:+5.1f} "
              f"r5={f['r5']:+6.1f}% 52w={f['pct_52w_high']:5.1f}% vol×{f['volratio']}")


if __name__ == "__main__":
    main()
