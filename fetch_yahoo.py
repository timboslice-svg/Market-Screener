"""Fetch daily histories from Yahoo Finance v8 chart API (stdlib only).
Cookie-bootstrapped (Yahoo 429s cookieless clients). Resumable: skips complete files.
Writes data/<name>.csv with DIVIDEND-ADJUSTED OHLC.
"""
import http.cookiejar
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.addheaders = [("User-Agent", UA), ("Accept", "*/*"),
                     ("Accept-Language", "en-US,en;q=0.9")]

CRUMB = ""


def bootstrap():
    """Collect Yahoo cookies (fc.yahoo.com sets them even on 404), then a crumb."""
    global CRUMB
    for url in ["https://fc.yahoo.com", "https://finance.yahoo.com"]:
        try:
            opener.open(url, timeout=20).read()
        except Exception:
            pass  # 404/redirect still sets cookies
    time.sleep(1.0)
    for host in ["query1", "query2"]:
        try:
            r = opener.open(f"https://{host}.finance.yahoo.com/v1/test/getcrumb", timeout=20)
            CRUMB = r.read().decode().strip()
            if CRUMB and "<" not in CRUMB:
                print(f"[bootstrap] cookies={len(jar)} crumb=yes")
                return
        except Exception as e:
            print(f"[bootstrap] crumb via {host} failed: {str(e)[:60]}")
    CRUMB = ""
    print(f"[bootstrap] cookies={len(jar)} crumb=NO (chart API may still work)")


SYMBOLS = {
    "spy.us": "SPY", "qqq.us": "QQQ", "iwm.us": "IWM", "dia.us": "DIA",
    "efa.us": "EFA", "eem.us": "EEM", "spx": "^GSPC", "ndx": "^NDX",
    "tlt.us": "TLT", "ief.us": "IEF", "shy.us": "SHY", "agg.us": "AGG",
    "lqd.us": "LQD", "hyg.us": "HYG",
    "xlk.us": "XLK", "xlf.us": "XLF", "xle.us": "XLE", "xlv.us": "XLV",
    "xli.us": "XLI", "xlp.us": "XLP", "xlu.us": "XLU", "xly.us": "XLY", "xlb.us": "XLB",
    "mtum.us": "MTUM", "vlue.us": "VLUE", "qual.us": "QUAL", "usmv.us": "USMV",
    "splv.us": "SPLV", "sphb.us": "SPHB", "ijs.us": "IJS", "vug.us": "VUG", "vtv.us": "VTV",
    "sso.us": "SSO", "upro.us": "UPRO", "gld.us": "GLD", "vnq.us": "VNQ", "rsp.us": "RSP",
    "vix": "^VIX", "vix3m": "^VIX3M", "vvix": "^VVIX",
    "svxy.us": "SVXY", "vixy.us": "VIXY", "vxz.us": "VXZ", "vixm.us": "VIXM",
    "put": "^PUT", "bxm": "^BXM", "bxy": "^BXY", "cll": "^CLL", "cndr": "^CNDR",
    "smh.us": "SMH", "iyt.us": "IYT",
    "es.f": "ES=F", "nq.f": "NQ=F", "zn.f": "ZN=F", "gc.f": "GC=F",
    "cl.f": "CL=F", "dx.f": "DX=F", "si.f": "SI=F", "hg.f": "HG=F",
    "ewj.us": "EWJ", "ewg.us": "EWG", "ewu.us": "EWU", "ewq.us": "EWQ",
    "ewa.us": "EWA", "ewc.us": "EWC", "ewh.us": "EWH", "ews.us": "EWS",
    "eww.us": "EWW", "ewz.us": "EWZ", "fxi.us": "FXI", "ewt.us": "EWT",
    "ewy.us": "EWY", "ewl.us": "EWL", "ewp.us": "EWP", "ewi.us": "EWI",
    "ewd.us": "EWD", "ewn.us": "EWN", "ewo.us": "EWO", "ewk.us": "EWK", "eza.us": "EZA",
}
STOCKS = """aapl msft ibm ge ko pg jnj xom cvx wmt jpm bac wfc c mrk pfe intc csco orcl hd
mcd dis ba cat mmm hon ups fdx nke sbux txn qcom amgn gild adbe crm nvda amd mu t vz cmcsa
pep cl kmb mo abt bmy lly unh cvs axp gs ms usb pnc tgt low cost emr""".split()
for s in STOCKS:
    SYMBOLS[f"{s}.us"] = s.upper()


def fetch(ticker, attempt):
    host = "query1" if attempt % 2 == 0 else "query2"
    url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(ticker)}?range=max&interval=1d&events=div%2Csplit")
    if CRUMB:
        url += "&crumb=" + urllib.parse.quote(CRUMB)
    with opener.open(url, timeout=30) as r:
        return json.loads(r.read().decode())


def write_csv(name, payload):
    res = payload["chart"]["result"][0]
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
    rows = []
    from datetime import datetime, timezone
    for i, t in enumerate(ts):
        o, h, l, cl = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        v = q["volume"][i] if q.get("volume") else 0
        if cl is None or o is None or cl == 0:
            continue
        a = adj[i] if adj and adj[i] is not None else cl
        f = a / cl
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        rows.append((d.isoformat(), o * f, (h or o) * f, (l or o) * f, a, v or 0))
    if not rows:
        return 0, None, None
    path = os.path.join(DATA, f"{name}.csv")
    with open(path, "w") as fh:
        fh.write("Date,Open,High,Low,Close,Volume\n")
        for r in rows:
            fh.write(f"{r[0]},{r[1]:.6f},{r[2]:.6f},{r[3]:.6f},{r[4]:.6f},{int(r[5])}\n")
    return len(rows), rows[0][0], rows[-1][0]


def complete(name):
    path = os.path.join(DATA, f"{name}.csv")
    try:
        with open(path) as fh:
            head = fh.readline()
            if not head.startswith("Date,"):
                return False
            return sum(1 for _ in fh) >= 100
    except Exception:
        return False


def main():
    bootstrap()
    man_path = os.path.join(DATA, "MANIFEST.txt")
    man = open(man_path, "w")
    ok = bad = skipped = 0
    consecutive_429 = 0
    for name, ticker in SYMBOLS.items():
        if complete(name):
            skipped += 1
            ok += 1
            man.write(f"{name},{ticker},cached,,,ok\n")
            continue
        n, first, last, err = 0, None, None, ""
        for attempt in range(5):
            try:
                payload = fetch(ticker, attempt)
                n, first, last = write_csv(name, payload)
                consecutive_429 = 0
                break
            except urllib.error.HTTPError as e:
                err = f"HTTP {e.code}"
                if e.code == 429:
                    consecutive_429 += 1
                    time.sleep(min(8.0 * (attempt + 1), 30))
                elif e.code == 404:
                    break  # symbol not on yahoo
                else:
                    time.sleep(3.0)
            except Exception as e:
                err = str(e)[:60]
                time.sleep(3.0)
        status = "ok" if n >= 100 else ("SHORT" if n > 0 else f"BAD({err})")
        ok += 1 if n >= 100 else 0
        bad += 0 if n >= 100 else 1
        line = f"{name},{ticker},{n},{first},{last},{status}"
        print(line, flush=True)
        man.write(line + "\n")
        if consecutive_429 >= 8:
            print("ABORT: sustained 429 — Yahoo is blocking this IP entirely.", flush=True)
            man.write("ABORT,429\n")
            break
        time.sleep(0.7)
    man.close()
    print(f"DONE ok={ok} bad={bad} (cached {skipped})")


if __name__ == "__main__":
    main()
