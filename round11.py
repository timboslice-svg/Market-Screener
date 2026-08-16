"""Round 11: 'idiosyncratic oversold' event study on single stocks — the price-only
core of the screener premise. SURVIVORSHIP-BIASED universe (all names survived to
today), therefore results are an UPPER BOUND: a fail here kills the price-only
premise outright; a pass is merely 'not disproven'.
Event: stock falls >= DROP% over WIN trading days while SPY falls < MKT_CAP% —
i.e. the drop is idiosyncratic, not market-driven. Entry next close, forward
20d/60d excess return vs SPY. Variants condition on prior health (near 52w high
before the drop). Run: python3 round11.py"""
import numpy as np
import pandas as pd
from harness import close, load

spy = close("spy.us")
spyr = spy.pct_change()

STOCKS = """aapl.us msft.us ibm.us ge.us ko.us pg.us jnj.us xom.us cvx.us wmt.us
jpm.us bac.us wfc.us c.us mrk.us pfe.us intc.us csco.us orcl.us hd.us mcd.us dis.us ba.us cat.us
mmm.us hon.us ups.us fdx.us nke.us sbux.us txn.us qcom.us amgn.us gild.us adbe.us crm.us nvda.us
amd.us mu.us t.us vz.us cmcsa.us pep.us cl.us kmb.us mo.us abt.us bmy.us lly.us unh.us cvs.us
axp.us gs.us ms.us usb.us pnc.us tgt.us low.us cost.us emr.us""".split()


def event_study(drop, win, mkt_cap, healthy_filter, name, cooloff=21):
    rows = []
    for s in STOCKS:
        try:
            c = close(s)
        except Exception:
            continue
        c = c[c.index >= "1995-01-01"]
        if len(c) < 500:
            continue
        r_win = c / c.shift(win) - 1
        spy_al = spy.reindex(c.index).ffill()
        spy_win = spy_al / spy_al.shift(win) - 1
        near_high = (c / c.rolling(252).max()).shift(win + 21)  # health measured before the drop
        sig = (r_win <= -drop) & (spy_win >= -mkt_cap)
        if healthy_filter:
            sig &= near_high >= 0.90
        sig = sig.fillna(False)
        last_event = None
        for dt in c.index[sig.values]:
            if last_event is not None and (dt - last_event).days < cooloff * 1.6:
                continue  # avoid overlapping events on the same name
            last_event = dt
            i = c.index.get_loc(dt)
            for h, tag in [(20, "20d"), (60, "60d")]:
                if i + 1 + h >= len(c):
                    continue
                entry = c.iloc[i + 1]
                fwd = c.iloc[i + 1 + h] / entry - 1
                sfwd = spy_al.iloc[i + 1 + h] / spy_al.iloc[i + 1] - 1
                rows.append({"stock": s, "date": dt, "h": tag, "ex": fwd - sfwd})
    ev = pd.DataFrame(rows)
    if ev.empty:
        print(f"{name}: no events")
        return None
    out = []
    for tag in ["20d", "60d"]:
        e = ev[ev["h"] == tag]["ex"]
        n = len(e)
        t = e.mean() / e.std() * np.sqrt(n) if n > 2 and e.std() > 0 else np.nan
        out.append(f"{tag}: n={n:4d} mean_ex={e.mean()*100:+.2f}% med={e.median()*100:+.2f}% "
                   f"hit={((e > 0).mean())*100:.0f}% t={t:.2f}")
    print(f"{name}\n  " + "\n  ".join(out))
    return ev


print("=" * 70)
print("Event studies (excess vs SPY after idiosyncratic drops), 1995-2026")
print("SURVIVORSHIP-BIASED — treat positive results as upper bounds")
print("=" * 70)
event_study(0.15, 10, 0.05, False, "E1: -15%/10d, mkt flat, no health filter")
event_study(0.15, 10, 0.05, True,  "E2: -15%/10d, mkt flat, was near 52w high (healthy)")
event_study(0.25, 21, 0.07, False, "E3: -25%/21d, mkt flat (big idiosyncratic crash)")
event_study(0.25, 21, 0.07, True,  "E4: -25%/21d, healthy before")
event_study(0.10, 1, 0.03, False,  "E5: -10% single day, mkt flat (earnings-shock style)")
event_study(0.10, 1, 0.03, True,   "E6: -10% single day, healthy before")
print("\nControl (baseline drift): random-entry excess should be ~0 by construction of excess returns.")
