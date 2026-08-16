"""Independent second data source (stdlib only):
- CBOE direct daily CSVs: VIX, VIX3M, PUT, BXM, BXY, CLL, CNDR
- Ken French library: daily factors, momentum factor, 10 momentum deciles,
  49 industry portfolios (survivorship-free, back to 1926).
Only writes files that are missing/incomplete (Yahoo takes precedence for overlaps).
"""
import io
import os
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def complete(name, min_rows=100):
    try:
        with open(os.path.join(DATA, name)) as fh:
            if not fh.readline().startswith("Date"):
                return False
            return sum(1 for _ in fh) >= min_rows
    except Exception:
        return False


log = []

# ---------- CBOE ----------
CBOE = {
    "vix.csv": "VIX_History.csv", "vix3m.csv": "VIX3M_History.csv",
    "put.csv": "PUT_History.csv", "bxm.csv": "BXM_History.csv",
    "bxy.csv": "BXY_History.csv", "cll.csv": "CLL_History.csv",
    "cndr.csv": "CNDR_History.csv",
}
for out, src in CBOE.items():
    if complete(out):
        log.append(f"{out}: cached")
        continue
    try:
        raw = get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{src}").decode()
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        hdr = lines[0].upper().replace('"', "").split(",")
        rows = []
        for l in lines[1:]:
            p = l.replace('"', "").split(",")
            if len(p) < 2 or "/" not in p[0] and "-" not in p[0]:
                continue
            d = p[0]
            if "/" in d:  # MM/DD/YYYY -> ISO
                m, dd, y = d.split("/")
                d = f"{y}-{int(m):02d}-{int(dd):02d}"
            if len(p) >= 5:
                o, h, lo, c = p[1], p[2], p[3], p[4]
            else:
                o = h = lo = c = p[1]
            try:
                float(c)
            except ValueError:
                continue
            rows.append(f"{d},{o},{h},{lo},{c},0")
        if len(rows) >= 100:
            with open(os.path.join(DATA, out), "w") as fh:
                fh.write("Date,Open,High,Low,Close,Volume\n")
                fh.write("\n".join(rows) + "\n")
            log.append(f"{out}: {len(rows)} rows from CBOE")
        else:
            log.append(f"{out}: CBOE gave {len(rows)} rows (FAIL)")
    except Exception as e:
        log.append(f"{out}: CBOE error {str(e)[:60]}")
    time.sleep(0.5)

# ---------- Ken French ----------
FF_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"


def parse_ff(text, out, colnames=None):
    """Parse first daily block of a French CSV: date rows are 8-digit ints."""
    lines = text.splitlines()
    start = None
    header_idx = None
    for i, l in enumerate(lines):
        s = l.split(",")[0].strip()
        if len(s) == 8 and s.isdigit():
            start = i
            break
        if l.strip() and "," in l:
            header_idx = i
    if start is None:
        return 0
    cols = None
    if header_idx is not None:
        cols = [c.strip() for c in lines[header_idx].split(",")]
        if cols and cols[0] == "":
            cols = cols[1:]
    if colnames:
        cols = colnames
    rows = []
    for l in lines[start:]:
        p = [x.strip() for x in l.split(",")]
        d = p[0]
        if len(d) != 8 or not d.isdigit():
            break  # end of first block
        vals = p[1:]
        rows.append((f"{d[:4]}-{d[4:6]}-{d[6:]}", vals))
    if not rows:
        return 0
    ncol = len(rows[0][1])
    if not cols or len(cols) != ncol:
        cols = [f"c{i}" for i in range(ncol)]
    with open(os.path.join(DATA, out), "w") as fh:
        fh.write("Date," + ",".join(cols) + "\n")
        for d, vals in rows:
            fh.write(d + "," + ",".join(vals) + "\n")
    return len(rows)


FF = [
    ("F-F_Research_Data_Factors_daily_CSV.zip", "ff_factors.csv", ["MktRF", "SMB", "HML", "RF"]),
    ("F-F_Momentum_Factor_daily_CSV.zip", "ff_mom.csv", ["Mom"]),
    ("10_Portfolios_Prior_12_2_Daily_CSV.zip", "ff_mom10.csv", None),
    ("49_Industry_Portfolios_Daily_CSV.zip", "ff_ind49.csv", None),
]
for zname, out, cols in FF:
    if complete(out, 1000):
        log.append(f"{out}: cached")
        continue
    try:
        blob = get(FF_BASE + zname)
        zf = zipfile.ZipFile(io.BytesIO(blob))
        inner = zf.namelist()[0]
        text = zf.read(inner).decode("latin-1")
        n = parse_ff(text, out, cols)
        log.append(f"{out}: {n} rows from French library")
    except Exception as e:
        log.append(f"{out}: FF error {str(e)[:60]}")
    time.sleep(0.5)

with open(os.path.join(DATA, "MANIFEST_FB.txt"), "w") as fh:
    fh.write("\n".join(log) + "\n")
print("\n".join(log))
