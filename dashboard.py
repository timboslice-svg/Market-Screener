"""Render dashboard.html from flags.json + news.json (+ triage.json, ledger.csv)."""
import html
import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def esc(s):
    return html.escape(str(s or ""))


def main():
    with open(os.path.join(HERE, "flags.json")) as fh:
        flags = json.load(fh)
    with open(os.path.join(HERE, "news.json")) as fh:
        news = json.load(fh)
    triage = {}
    tp = os.path.join(HERE, "triage.json")
    if os.path.exists(tp):
        with open(tp) as fh:
            triage = {t["ticker"]: t for t in json.load(fh)}
    date = flags[0]["date"] if flags else "n/a"
    if triage:
        flags = sorted(flags, key=lambda f: -(triage.get(f["ticker"], {}).get("interesting", 0)))

    cal = {}
    cp = os.path.join(HERE, "calendar.json")
    if os.path.exists(cp):
        with open(cp) as fh:
            cal = json.load(fh)
    flag_earn = cal.get("flag_earnings", {})

    cards = []
    for f in flags:
        t = f["ticker"]
        tr = triage.get(t)
        hl = news.get(t, [])
        news_html = "".join(
            f'<li><a href="{esc(h["link"])}" target="_blank">{esc(h["title"])}</a>'
            f' <span class="src">{esc(h.get("source",""))}</span></li>' for h in hl) or "<li class='src'>no headlines found</li>"
        tri_html = ""
        if tr:
            cat = esc(tr.get("category", "unclear"))
            tri_html = (f'<div class="triage {cat}"><b>{esc(tr.get("interesting","?"))}/10</b> '
                        f'<span class="cat">{cat}</span><br>{esc(tr.get("rationale",""))}</div>')
        side = "neg" if f["side"] == "down" else "pos"
        ebadge = ""
        if t in flag_earn:
            ebadge = f' <span class="ebadge">📊 earnings {esc(flag_earn[t][5:])}</span>'
        if t in cal.get("flag_exdiv", {}):
            ebadge += f' <span class="ebadge">💰 ex-div {esc(cal["flag_exdiv"][t][5:])}</span>'
        cards.append(f"""
<div class="card {side}">
  <div class="head"><b>{esc(t)}</b> {esc(f['name'])} <span class="region">{esc(f['region'])}</span>
    <span class="mv {side}">{f['r5']:+.1f}% / 5d</span>{ebadge}</div>
  <div class="stats">z1 {f['z1']:+.1f} · z5 {f['z5']:+.1f} · vol×{esc(f['volratio'])} ·
    {f['pct_52w_high']:.0f}% of 52w high</div>
  {tri_html}
  <ul class="news">{news_html}</ul>
</div>""")

    overview_html = ""
    op = os.path.join(HERE, "overview.json")
    if os.path.exists(op):
        with open(op) as fh:
            ov = json.load(fh)
        cells_html = ""
        for m in ov.get("markets", []):
            r1 = m.get("r1")
            cls = "pos" if (r1 or 0) >= 0 else "neg"
            cells_html += (f'<div class="mcell"><div class="mname">{esc(m["name"])}</div>'
                           f'<div class="mv {cls}">{r1:+.1f}%</div>'
                           f'<div class="msub">5d {m.get("r5") if m.get("r5") is not None else "-"}% · '
                           f'1m {m.get("r21") if m.get("r21") is not None else "-"}%</div></div>')
        b = ov.get("breadth", {})
        note = ov.get("ai_note", "")
        note_html = f'<div class="ainote">{esc(note)}</div>' if note else ""
        overview_html = (f'<div class="overview"><div class="mgrid">{cells_html}</div>'
                        f'<div class="breadth">Breadth: {b.get("pct_up_1d","?")}% of '
                        f'{b.get("n_stocks","?")} stocks up today · {b.get("pct_above_50dma","?")}% above 50-day average · '
                        f'median move {b.get("median_1d","?")}% · flags {b.get("flags_up","?")}▲ {b.get("flags_down","?")}▼</div>'
                        f'{note_html}</div>')

    cal_html = ""
    if cal.get("events"):
        ICONS = {"macro": "🏛", "earnings": "📊", "structural": "⚙️", "edge": "⭐"}
        by_date = {}
        for e in cal["events"]:
            by_date.setdefault(e["date"], []).append(e)
        rows_html = ""
        for d in sorted(by_date)[:14]:
            try:
                import datetime as _dt
                label = _dt.date.fromisoformat(d).strftime("%a %d %b")
            except ValueError:
                label = d
            items = " · ".join(f"{ICONS.get(e['tag'], '•')} {esc(e['name'])}" for e in by_date[d])
            rows_html += f'<div class="calrow"><span class="caldate">{label}</span> {items}</div>'
        cal_html = (f'<div class="calendar"><b>📅 Upcoming events</b>{rows_html}'
                    f'<div class="src">⭐ = structurally strong days (turn-of-month / pre-holiday, '
                    f'see research); earnings from rolling cache — verify before trading around them.</div></div>')

    ledger_html = ""
    lp = os.path.join(HERE, "ledger.csv")
    if os.path.exists(lp):
        led = pd.read_csv(lp)
        res = led.dropna(subset=["fwd20x"])
        if len(res):
            s = []
            for side in ["down", "up"]:
                e = res[res["side"] == side]["fwd20x"]
                if len(e):
                    s.append(f"{side}: n={len(e)}, mean 20d excess {e.mean():+.2f}%, hit {(e>0).mean()*100:.0f}%")
            ledger_html = f"<div class='ledger'><b>Track record</b> ({len(led)} flags, {len(res)} resolved): " \
                          + " · ".join(s) + "</div>"

    import datetime
    gen_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="240">
<title>Screener — {esc(date)}</title><style>
body{{font-family:-apple-system,Segoe UI,sans-serif;margin:20px auto;max-width:900px;
     background:#111;color:#ddd}}
h1{{font-size:20px}} .card{{border:1px solid #333;border-left:4px solid #555;border-radius:8px;
     padding:10px 14px;margin:10px 0;background:#1a1a1a}}
.card.neg{{border-left-color:#c0392b}} .card.pos{{border-left-color:#27ae60}}
.head{{font-size:15px}} .region{{background:#333;border-radius:4px;padding:1px 6px;font-size:11px}}
.mv.neg{{color:#e74c3c}} .mv.pos{{color:#2ecc71}} .stats{{color:#888;font-size:12px;margin:4px 0}}
.news{{margin:6px 0 2px 18px;padding:0;font-size:13px}} .news li{{margin:2px 0}}
.news a{{color:#6cf;text-decoration:none}} .src{{color:#777;font-size:11px}}
.triage{{background:#222;border-radius:6px;padding:6px 10px;font-size:13px;margin:6px 0}}
.triage .cat{{color:#f39c12}} .ledger{{margin:16px 0;padding:10px;background:#1a1a2a;border-radius:8px;font-size:13px}}
.overview{{margin:14px 0;padding:12px;background:#161622;border-radius:10px}}
.mgrid{{display:flex;flex-wrap:wrap;gap:10px}}
.mcell{{min-width:96px;padding:6px 8px;background:#1e1e2e;border-radius:8px}}
.mname{{font-size:11px;color:#999}} .mcell .mv{{font-size:15px;font-weight:600}}
.msub{{font-size:10px;color:#777}}
.breadth{{margin-top:10px;font-size:12px;color:#aab}}
.ainote{{margin-top:10px;font-size:13px;color:#cce;border-left:3px solid #46a;padding-left:10px}}
.calendar{{margin:14px 0;padding:12px;background:#151d15;border-radius:10px;font-size:13px}}
.calrow{{margin:5px 0;color:#cdc}}
.caldate{{display:inline-block;min-width:92px;color:#8a8;font-weight:600}}
.ebadge{{background:#3a2f10;color:#f0c040;border-radius:4px;padding:1px 6px;font-size:11px}}
</style></head><body>
<h1>Nightly screener — {esc(date)} · {len(flags)} flags</h1>
<p class="src">Generated {gen_at} · auto-reloads every 4 min · research triage only —
not investment advice. Sorted by {'AI interestingness' if triage else 'move size'}.</p>
{overview_html}
{cal_html}
{ledger_html}
{''.join(cards)}
</body></html>"""
    out = os.path.join(HERE, "dashboard.html")
    with open(out, "w") as fh:
        fh.write(page)
    print(f"dashboard: {out}")


if __name__ == "__main__":
    main()
