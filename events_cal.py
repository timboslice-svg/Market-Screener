"""Event calendar: rule-based market structure + static macro dates + rolling
earnings cache (yfinance). Writes calendar.json. Run after scan.py.
(NB: named events_cal.py because 'calendar.py' shadows the stdlib module.)"""
import datetime as dt
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HORIZON = 21          # days ahead to show
EARN_BATCH = 120      # universe names refreshed per night (full sweep ~weekly)

US_HOLIDAYS = {  # market holidays (refresh each January)
    2026: [(1, 1), (1, 19), (2, 16), (4, 3), (5, 25), (6, 19), (7, 3), (9, 7), (11, 26), (12, 25)],
    2027: [(1, 1), (1, 18), (2, 15), (3, 26), (5, 31), (6, 18), (7, 5), (9, 6), (11, 25), (12, 24)],
}


def holidays(year):
    return {dt.date(year, m, d) for m, d in US_HOLIDAYS.get(year, [])}


def is_trading_day(d):
    return d.weekday() < 5 and d not in holidays(d.year)


def trading_days_of_month(year, month):
    d = dt.date(year, month, 1)
    out = []
    while d.month == month:
        if is_trading_day(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def nth_weekday(year, month, weekday, n):
    d = dt.date(year, month, 1)
    count = 0
    while d.month == month:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += dt.timedelta(days=1)
    return None


def rule_based_events(today):
    events = []
    for k in range(3):  # this month + next two
        y = today.year + (today.month - 1 + k) // 12
        m = (today.month - 1 + k) % 12 + 1
        nfp = nth_weekday(y, m, 4, 1)  # first Friday
        if nfp:
            events.append((nfp, "US jobs report (NFP)", "macro"))
        opx = nth_weekday(y, m, 4, 3)  # third Friday
        if opx:
            nm = ("Quad witching + S&P rebalance effective" if m in (3, 6, 9, 12)
                  else "Monthly options expiry")
            events.append((opx, nm, "structural"))
        # VIX futures expiry: the Wednesday 30 days before NEXT month's 3rd Friday
        y2 = y + (m // 12)
        m2 = m % 12 + 1
        tf_next = nth_weekday(y2, m2, 4, 3)
        if tf_next:
            vx = tf_next - dt.timedelta(days=30)
            if vx.month == m:
                events.append((vx, "VIX futures expiry", "structural"))
        # Russell reconstitution: last Friday of June
        if m == 6:
            lf = max(d for d in trading_days_of_month(y, 6) if d.weekday() == 4)
            events.append((lf, "Russell reconstitution (huge forced flows)", "structural"))
        # US federal election day (even years): first Tuesday after first Monday, November
        if m == 11 and y % 2 == 0:
            fm = nth_weekday(y, 11, 0, 1)
            events.append((fm + dt.timedelta(days=1), "US election day", "macro"))
        tds = trading_days_of_month(y, m)
        if len(tds) >= 4:
            events.append((tds[-4], "Turn-of-month window begins (TOM edge days)", "edge"))
        for mm, dd in US_HOLIDAYS.get(y, []):
            hol = dt.date(y, mm, dd)
            if hol.month == m:
                prev = hol - dt.timedelta(days=1)
                while prev.weekday() >= 5 or prev in holidays(prev.year):
                    prev -= dt.timedelta(days=1)
                events.append((prev, "Pre-holiday session (historically strong)", "edge"))
    return events


def static_events():
    out = []
    path = os.path.join(HERE, "calendar_static.csv")
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        next(fh)
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split(",")
            if len(p) >= 3:
                try:
                    out.append((dt.date.fromisoformat(p[0]), p[1], p[2]))
                except ValueError:
                    pass
    return out


def earnings_events(today):
    """Rolling cache: refresh flagged names always + oldest EARN_BATCH universe names."""
    try:
        import yfinance as yf
    except ImportError:
        return [], {}, {}
    cache_path = os.path.join(HERE, "earnings_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path) as fh:
            cache = json.load(fh)
    tickers = []
    with open(os.path.join(HERE, "universe.csv")) as fh:
        next(fh)
        tickers = [l.split(",")[0] for l in fh if l.strip()]
    flagged = []
    try:
        with open(os.path.join(HERE, "flags.json")) as fh:
            flagged = [f["ticker"] for f in json.load(fh)]
    except Exception:
        pass
    now = today.isoformat()

    def staleness(t):
        return cache.get(t, {}).get("checked", "1970-01-01")

    todo = list(dict.fromkeys(flagged + sorted(tickers, key=staleness)[:EARN_BATCH]))

    def iso(v):
        v0 = v[0] if isinstance(v, (list, tuple)) and v else v
        if v0 is None:
            return None
        return v0.isoformat()[:10] if hasattr(v0, "isoformat") else str(v0)[:10]

    for t in todo:
        try:
            cal = yf.Ticker(t).calendar
            ed = xd = None
            if isinstance(cal, dict):
                ed = iso(cal.get("Earnings Date"))
                xd = iso(cal.get("Ex-Dividend Date"))
            elif cal is not None and hasattr(cal, "index"):  # older yfinance: DataFrame
                if "Earnings Date" in getattr(cal, "index", []):
                    ed = iso(list(cal.loc["Earnings Date"]))
                if "Ex-Dividend Date" in getattr(cal, "index", []):
                    xd = iso(list(cal.loc["Ex-Dividend Date"]))
            cache[t] = {"date": ed, "exdiv": xd, "checked": now}
        except Exception:
            old = cache.get(t, {})
            cache[t] = {"date": old.get("date"), "exdiv": old.get("exdiv"), "checked": now}
        time.sleep(0.25)
    with open(cache_path, "w") as fh:
        json.dump(cache, fh)

    events, flag_earn, flag_exdiv = [], {}, {}
    horizon_end = today + dt.timedelta(days=HORIZON)
    by_date = {}
    for t, info in cache.items():
        ds = info.get("date")
        if ds:
            try:
                d = dt.date.fromisoformat(ds[:10])
                if today <= d <= horizon_end:
                    by_date.setdefault(d, []).append(t)
                if t in flagged and today <= d <= today + dt.timedelta(days=14):
                    flag_earn[t] = ds[:10]
            except ValueError:
                pass
        xs = info.get("exdiv")
        if xs and t in flagged:
            try:
                x = dt.date.fromisoformat(xs[:10])
                if today <= x <= today + dt.timedelta(days=14):
                    flag_exdiv[t] = xs[:10]
            except ValueError:
                pass
    for d, ts in by_date.items():
        ts = sorted(ts)
        label = ", ".join(ts[:8]) + (f" +{len(ts)-8} more" if len(ts) > 8 else "")
        events.append((d, f"Earnings: {label}", "earnings"))
    return events, flag_earn, flag_exdiv


def main():
    today = dt.date.today()
    events = rule_based_events(today) + static_events()
    earn, flag_earn, flag_exdiv = earnings_events(today)
    events += earn
    horizon_end = today + dt.timedelta(days=HORIZON)
    events = sorted({(d.isoformat(), n, t) for d, n, t in events if today <= d <= horizon_end})
    out = {"generated": today.isoformat(),
           "events": [{"date": d, "name": n, "tag": t} for d, n, t in events],
           "flag_earnings": flag_earn, "flag_exdiv": flag_exdiv}
    with open(os.path.join(HERE, "calendar.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"calendar: {len(out['events'])} events in next {HORIZON}d, "
          f"{len(flag_earn)} flagged w/ earnings, {len(flag_exdiv)} w/ ex-div")


if __name__ == "__main__":
    main()
