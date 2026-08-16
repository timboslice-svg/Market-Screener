"""Plan B for ETF data: yfinance (uses browser-impersonation, usually beats 429).
Only fetches what's missing. Requires: pip3 install --user yfinance
"""
import os
import time

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("yfinance not installed — run: pip3 install --user yfinance")

from fetch_yahoo import SYMBOLS, DATA, complete


def main():
    ok = bad = skipped = 0
    for name, ticker in SYMBOLS.items():
        if complete(name):
            skipped += 1
            continue
        try:
            df = yf.download(ticker, period="max", interval="1d", auto_adjust=True,
                             progress=False, threads=False)
            if df is None or len(df) < 100:
                print(f"{name},{ticker},EMPTY", flush=True)
                bad += 1
                continue
            if hasattr(df.columns, "levels"):  # flatten MultiIndex columns
                df.columns = [c[0] for c in df.columns]
            out = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            out.index.name = "Date"
            out.to_csv(os.path.join(DATA, f"{name}.csv"), float_format="%.6f")
            print(f"{name},{ticker},{len(out)},{out.index[0].date()},{out.index[-1].date()},ok", flush=True)
            ok += 1
        except Exception as e:
            print(f"{name},{ticker},ERR({str(e)[:60]})", flush=True)
            bad += 1
        time.sleep(0.5)
    print(f"DONE ok={ok} bad={bad} cached={skipped}")


if __name__ == "__main__":
    main()
