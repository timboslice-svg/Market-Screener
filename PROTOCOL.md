# Equity Strategy Research — Pre-registered Protocol (2026-07-30)

Goal: find strategies that outperform S&P 500 TOTAL RETURN (SPY adjusted) consistently.

## Rules (fixed before any results are seen)
1. Benchmark = SPY dividend-adjusted close-to-close ("total return"). Never price-only SPX.
2. All signals use data through close of day t; positions earn day t+1 returns. No look-ahead.
3. Transaction costs per side, charged on |Δposition|:
   - SPY/QQQ/IWM/TLT/IEF/SHY/AGG/GLD: 1.0 bp
   - Sector SPDRs, EFA/EEM, VNQ, LQD/HYG: 2.5 bp
   - Factor ETFs (MTUM/VLUE/QUAL/USMV/SPLV/SPHB/IJS): 3.0 bp
   - Leveraged (SSO/UPRO): 3.0 bp
4. Cash earns SHY daily return. Leverage financed at cash + 50 bps/yr on levered portion.
5. ACCEPT a hypothesis only if, NET of costs, versus SPY on the strategy's own sample:
   a) excess CAGR > 0, AND
   b) excess return same sign in BOTH calendar halves of the sample, AND
   c) t-stat of daily excess returns >= 1.5, AND
   d) >= 55% of rolling 12-month windows beat SPY.
6. RISK-ADJUSTED note: if Sharpe beats SPY by >= 0.15 but raw return doesn't, mark
   "RA-ONLY" (usable via leverage, tested separately) — not an accept by itself.
7. Anything that fails: REJECT, do not re-litigate without new data or new mechanism.
8. Multiple testing: with ~13 hypotheses in round 1, expect ~1 false pass at these
   thresholds; any round-1 accept must survive a round-2 robustness sweep
   (parameter perturbation ±25%, subperiod stability) before being called promising.

## Known traps this protocol guards against
- Dividend trap (price-only benchmark), look-ahead, survivorship (ETF-level tests only
  in round 1; no current-constituent stock lists backtested into the past),
- Overnight strategies: 2 sides/day means ~5 bp/day drag — must be netted.
- Leveraged ETF expense ratios are embedded in their price series (good).
