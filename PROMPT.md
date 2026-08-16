# Triage prompt (agent mode)

When a Claude Code agent runs the nightly pipeline instead of the API script, it should,
after `scan.py` + `news.py`, read `flags.json` + `news.json` and write `triage.json`:
an array of `{ticker, category, interesting, rationale, cited}` where

- `category`: `real-deterioration` | `flow-or-sentiment` | `unclear`
  Judge ONLY from the provided headlines and stats. Signs of flow-or-sentiment:
  index-exclusion, fund liquidation, analyst downgrade without new facts, sector
  sympathy moves, no news at all despite a big idiosyncratic move.
  Signs of real deterioration: guidance cuts, missed earnings, regulatory action,
  fraud, loss of a major customer, dilutive raises.
- `interesting` (0-10): worth Tim's research time TONIGHT. Weight higher: large
  idiosyncratic drops with benign/absent news (the round-11 lesson: drops in
  previously-healthy names are usually justified — an unexplained one is the rare
  exception worth attention). Weight lower: moves fully explained by the news.
- `rationale`: max 2 sentences, cite specific headlines by index.
- `cited`: array of headline indices used.

Additionally, read `overview.json` (markets + breadth) and write a 4-6 sentence
overall-situation assessment into its `ai_note` field: which regions/assets moved and
why it matters, what breadth says about participation, and the common thread (if any)
across tonight's flags.

Then run `dashboard.py`. Never phrase output as investment advice or buy/sell
recommendations — this is a research attention filter; decisions are Tim's.

Evidence base (from the 2026-07 research loop, round 11): after idiosyncratic drops
(−15%/10d, market flat) stocks showed +5.5% median-positive 60d excess in a
survivorship-biased sample (upper bound), BUT the effect disappears for stocks that
were near 52w highs before the drop — price alone cannot separate opportunity from
justified repricing. The news classification above is the load-bearing step.
