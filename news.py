"""Stage 2: pull free headlines for every flagged name (Google News RSS +
Yahoo Finance RSS). Writes news.json. Run after scan.py."""
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def rss_items(url, limit=6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            root = ET.fromstring(r.read())
        out = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            src = item.findtext("source") or ""
            if title and link:
                out.append({"title": title, "link": link, "date": pub, "source": src})
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def main():
    with open(os.path.join(HERE, "flags.json")) as fh:
        flags = json.load(fh)
    news = {}
    for f in flags:
        q = urllib.parse.quote(f'"{f["name"]}" stock when:4d')
        items = rss_items(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
        # Yahoo per-ticker feed as a second source (mostly US coverage)
        y = rss_items("https://feeds.finance.yahoo.com/rss/2.0/headline?s="
                      + urllib.parse.quote(f["ticker"]), limit=4)
        seen = {i["title"] for i in items}
        items += [i for i in y if i["title"] not in seen]
        news[f["ticker"]] = items[:8]
        print(f"news: {f['ticker']:<10} {len(news[f['ticker']])} items")
        time.sleep(0.6)
    with open(os.path.join(HERE, "news.json"), "w") as fh:
        json.dump(news, fh, indent=1)


if __name__ == "__main__":
    main()
