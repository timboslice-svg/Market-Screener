"""AI triage via OpenRouter (free models, with fallback chain) or Anthropic API.
Provider is picked from env: OPENROUTER_API_KEY first, else ANTHROPIC_API_KEY.
Writes triage.json + the overall ai_note into overview.json."""
import json
import os
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OR_KEY = os.environ.get("OPENROUTER_API_KEY")
AN_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not OR_KEY and not AN_KEY:
    raise SystemExit("triage: set OPENROUTER_API_KEY or ANTHROPIC_API_KEY — skipping")

PREFERRED = ["deepseek", "qwen", "glm", "kimi", "llama", "gemini", "mistral", "gpt-oss"]


def discover_free_models():
    """Ask OpenRouter which free models exist RIGHT NOW (the roster rotates)."""
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                     headers={"Authorization": f"Bearer {OR_KEY}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            models = json.loads(r.read()).get("data", [])
    except Exception as e:
        print(f"  [openrouter] model discovery failed ({str(e)[:60]}) — using static ids")
        return ["deepseek/deepseek-chat-v3-0324:free", "meta-llama/llama-3.3-70b-instruct:free"]
    free = []
    for m in models:
        p = m.get("pricing", {})
        if str(p.get("prompt", "1")) in ("0", "0.0") and m.get("id", "").endswith(":free"):
            free.append(m["id"])

    def rank(mid):
        for i, kw in enumerate(PREFERRED):
            if kw in mid.lower():
                return i
        return len(PREFERRED)

    free.sort(key=rank)
    print(f"  [openrouter] {len(free)} free models available; trying: {free[:6]}")
    return free[:6] or ["deepseek/deepseek-chat-v3-0324:free"]


OR_MODELS = ([os.environ.get("OPENROUTER_MODEL")] if os.environ.get("OPENROUTER_MODEL") else [])
if OR_KEY:
    OR_MODELS += discover_free_models()
AN_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

RUBRIC = """You are triaging stock-move flags for a nightly research brief. For EACH flag,
using ONLY the provided headlines and stats, output a JSON object:
 ticker, category (one of: real-deterioration | real-improvement | flow-or-sentiment | unclear),
 interesting (0-10: is this worth a human's research time tonight — weight idiosyncratic
 drops with benign/no news higher; obvious justified reactions lower),
 rationale (max 2 sentences, reference specific headlines),
 cited (array of headline indices used).
Rules: this is research triage, not investment advice. If headlines don't explain the
move, say so and mark unclear — an unexplained large idiosyncratic move is interesting.
If a flag notes upcoming EARNINGS, factor that in: a big move INTO earnings is often
positioning (note the event risk); a move with no news but imminent earnings may be leakage.
Return ONLY a JSON array of these objects, no other text."""


def call_openrouter(prompt):
    last_err = None
    for model in OR_MODELS:
        body = json.dumps({"model": model, "max_tokens": 4000,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://localhost/screener", "X-Title": "market-screener"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
            txt = out["choices"][0]["message"]["content"]
            if txt and txt.strip():
                print(f"  [openrouter] {model} ok")
                return txt
        except urllib.error.HTTPError as e:
            last_err = f"{model}: HTTP {e.code}"
            print(f"  [openrouter] {last_err} -> trying next model")
        except Exception as e:
            last_err = f"{model}: {str(e)[:60]}"
            print(f"  [openrouter] {last_err} -> trying next model")
    raise RuntimeError(f"all OpenRouter models failed ({last_err})")


def call_anthropic(prompt):
    body = json.dumps({"model": AN_MODEL, "max_tokens": 4000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": AN_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read())
    return "".join(b.get("text", "") for b in out.get("content", []))


def call_llm(prompt):
    if OR_KEY:
        try:
            return call_openrouter(prompt)
        except Exception as e:
            if not AN_KEY:
                raise
            print(f"  openrouter exhausted ({e}) -> anthropic fallback")
    return call_anthropic(prompt)


def main():
    with open(os.path.join(HERE, "flags.json")) as fh:
        flags = json.load(fh)
    with open(os.path.join(HERE, "news.json")) as fh:
        news = json.load(fh)
    flag_earn = {}
    try:
        with open(os.path.join(HERE, "calendar.json")) as fh:
            flag_earn = json.load(fh).get("flag_earnings", {})
    except Exception:
        pass
    triage = []
    for i in range(0, len(flags), 8):
        chunk = flags[i:i + 8]
        lines = []
        for f in chunk:
            hl = news.get(f["ticker"], [])
            hls = "\n".join(f"  [{j}] {h['title']} ({h.get('source','')})"
                            for j, h in enumerate(hl)) or "  (no headlines found)"
            earn_note = f" EARNINGS on {flag_earn[f['ticker']]}!" if f["ticker"] in flag_earn else ""
            lines.append(f"{f['ticker']} ({f['name']}, {f['region']}): r1={f['r1']}% z1={f['z1']} "
                         f"z5={f['z5']} vol×{f['volratio']} at {f['pct_52w_high']}% of 52w high, "
                         f"side={f['side']}.{earn_note}\n{hls}")
        txt = call_llm(RUBRIC + "\n\nFLAGS:\n\n" + "\n\n".join(lines))
        txt = txt[txt.find("["):txt.rfind("]") + 1]
        try:
            triage.extend(json.loads(txt))
        except Exception as e:
            print(f"triage: parse error on chunk {i}: {e}")
    with open(os.path.join(HERE, "triage.json"), "w") as fh:
        json.dump(triage, fh, indent=1)
    print(f"triage: {len(triage)} assessments written")

    # overall situation note -> overview.json ai_note
    ov_path = os.path.join(HERE, "overview.json")
    if os.path.exists(ov_path) and triage:
        with open(ov_path) as fh:
            ov = json.load(fh)
        top = sorted(triage, key=lambda t: -t.get("interesting", 0))[:6]
        prompt = ("Write a 4-6 sentence assessment of the overall market situation for a "
                  "nightly research brief (plain prose, no advice, no hedging boilerplate). "
                  "Cover: which regions/assets moved and why it matters, what breadth says "
                  "about participation, and the common thread (if any) in tonight's flags. "
                  "Return only the prose, no JSON.\n\n"
                  f"MARKETS: {json.dumps(ov.get('markets', []))}\n"
                  f"BREADTH: {json.dumps(ov.get('breadth', {}))}\n"
                  f"TOP FLAGS: {json.dumps(top)}")
        try:
            ov["ai_note"] = call_llm(prompt).strip()
            with open(ov_path, "w") as fh:
                json.dump(ov, fh, indent=1)
            print("overview: ai_note written")
        except Exception as e:
            print(f"overview note failed: {e}")


if __name__ == "__main__":
    main()
