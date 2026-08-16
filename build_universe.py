"""Build an expanded universe (~1000 names) from index constituent lists on
Wikipedia, falling back to the curated seed per region if a source fails.
Run occasionally (monthly): python3 build_universe.py"""
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
WIKI = "https://en.wikipedia.org/wiki/"


def fetch(page):
    req = urllib.request.Request(WIKI + page, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#39;", "'").strip()


def parse_tables(html):
    out = []
    for t in re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.S):
        rows = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
            rows.append([strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)])
        if rows:
            out.append(rows)
    return out


SOURCES = [
    # page, region, bench, suffix, ticker-validation regex, min rows to accept, cap
    ("List_of_S%26P_500_companies", "US", "^GSPC", "", r"^[A-Z][A-Z0-9.\-]{0,6}$", 400, 505),
    ("FTSE_100_Index", "UK", "^FTSE", ".L", r"^[A-Z0-9]{2,5}(\.[A-Z])?$", 60, 105),
    ("DAX", "DE", "^GDAXI", ".DE", r"^[A-Z0-9]{2,6}$", 25, 45),
    ("CAC_40", "FR", "^FCHI", ".PA", r"^[A-Z0-9]{1,6}$", 25, 45),
    ("Nikkei_225", "JP", "^N225", ".T", r"^\d{4}$", 100, 230),
    ("S%26P/ASX_50", "AU", "^AXJO", ".AX", r"^[A-Z0-9]{2,4}$", 25, 55),
    ("Straits_Times_Index", "SG", "^STI", ".SI", r"^[A-Z0-9]{2,5}$", 15, 35),
]
TICKER_HDR = re.compile(r"ticker|symbol|epic|code", re.I)
NAME_HDR = re.compile(r"company|name|constituent|security", re.I)


def harvest(page, region, bench, suffix, tickre, min_rows, cap):
    try:
        html = fetch(page)
    except Exception as e:
        print(f"[{region}] fetch failed: {e}")
        return []
    tickre_c = re.compile(tickre)
    best = []
    for rows in parse_tables(html):
        hdr = rows[0]
        ti = ni = None
        for i, h in enumerate(hdr):
            if ti is None and TICKER_HDR.search(h):
                ti = i
            if ni is None and NAME_HDR.search(h):
                ni = i
        if ti is None:
            continue
        got = []
        for r in rows[1:]:
            if len(r) <= ti:
                continue
            t = r[ti].strip().upper()
            t = re.sub(r"^(NYSE|NASDAQ|TYO|LSE|FRA|EPA|ASX|SGX):\s*", "", t)
            t = t.split()[0] if t else ""
            if not tickre_c.match(t):
                continue
            name = r[ni].strip() if (ni is not None and len(r) > ni and r[ni].strip()) else t
            yf = t.replace(".", "-") + suffix
            got.append((yf, name))
        if len(got) > len(best):
            best = got
    if len(best) < min_rows:
        print(f"[{region}] only {len(best)} rows parsed (<{min_rows}) — keeping seed only")
        return []
    print(f"[{region}] {len(best)} constituents")
    return [(t, n, region, bench) for t, n in best[:cap]]


def main():
    seed_path = os.path.join(HERE, "universe_seed.csv")
    uni_path = os.path.join(HERE, "universe.csv")
    if not os.path.exists(seed_path) and os.path.exists(uni_path):
        os.rename(uni_path, seed_path)  # first run: preserve curated seed
    rows = []
    seen = set()
    with open(seed_path) as fh:
        next(fh)
        for line in fh:
            p = line.rstrip("\n").split(",")
            if len(p) >= 4 and p[0] not in seen:
                seen.add(p[0])
                rows.append(p[:4])
    n_seed = len(rows)
    for page, region, bench, suffix, tickre, min_rows, cap in SOURCES:
        for t, name, reg, b in harvest(page, region, bench, suffix, tickre, min_rows, cap):
            if t not in seen:
                seen.add(t)
                rows.append([t, name.replace(",", " "), reg, b])
    with open(uni_path, "w") as fh:
        fh.write("ticker,name,region,bench\n")
        for r in rows:
            fh.write(",".join(r) + "\n")
    print(f"universe.csv: {len(rows)} names ({n_seed} seed + {len(rows)-n_seed} from indices)")


if __name__ == "__main__":
    main()
