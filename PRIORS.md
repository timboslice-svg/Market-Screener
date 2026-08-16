# Priors written BEFORE seeing any results (2026-07-30)

Recorded so that post-hoc rationalization is impossible. P(accept) = probability the
hypothesis passes the full pre-registered accept bar on our data.

| Hypothesis | Mechanism claimed | Prior P(accept) | Notes |
|---|---|---|---|
| B1 QQQ B&H | growth/tech beta, not alpha | 25% | likely wins on return, fails halves or w12 (2000-02 crash) |
| H1a/b Trend timing | crash avoidance | 5% | improves DD/Sharpe, almost never raw return. RA-ONLY likely |
| H2a Overnight | inventory risk premium | 15% | gross effect is real historically; 2bp/day cost is heavy; halves likely split |
| H2b Intraday | none | <2% | should be strongly negative — serves as harness sanity check |
| H3 Vol-managed | vol clustering, Moreira-Muir | 10% cap1 / 20% cap2 | cap2 with leverage has a real shot at raw return |
| H4 Turn-of-month | flow/rebalancing | 10% | old anomaly, holds ~35% of days; hard to beat B&H raw |
| H5 RSI(2) dip-buy | overreaction | 5% | in-market fraction too low to beat B&H raw |
| H6 Sector momentum | intermediate momentum | 15% | momentum is real but top3/9 concentration + 2000/2008 whipsaws |
| H7 Dual momentum | momentum + crash filter | 10% | same trend-timing problem vs raw SPY |
| H8/H9 factor ETFs | published factors | 10% | MTUM best shot; short samples |
| H10 SSO+MA200 | leverage where trend cuts tail | 30% | the structurally most plausible raw-return winner |
| H12 SSO TOM | leverage on seasonal | 10% | |
| H13 VIX<25 filter | vol regime | 5% | exits after crashes start, re-enters late |
| H15 RSP equal-weight | size/anti-concentration | 15% | won pre-2010, lost badly post-2015 mega-cap era → halves split |
| H16 Country momentum | momentum | 10% | US dominance post-2010 kills it vs SPY |
| H17 Sell-in-May | seasonal folklore | 5% | |
| H18 90/60 stack | diversification + leverage | 20% | 2022 bond crash hurts half2; Sharpe should beat |
| H19 SPY/GLD momentum | cross-asset momentum | 15% | gold 2004-11 and 2019-25 strong; 2011-18 dead |
| H20 52w-high proximity | anchoring | 5% | |
| H21 Lever-the-dips | mean reversion of crashes | 15% | works unless a dip keeps dipping (2008); financing drag |
| H22 VIX-spike→2x | crisis mean reversion | 15% | few events → wide CI; 2008 entry at VIX 35 was way early |
| H23 Trend×VolMgd | combo | 15% | |
| H24 QQQ+MA200 | beta + crash filter | 25% | QQQ beta may carry it past SPY even with timing drag |
| H25 SVXY VIX<20 | vol risk premium | 10% | Feb-2018 -90% day + 2020; VIX<20 filter didn't help in '18 |
| H28 Breadth gate | participation regime | 10% | |
| H29 Credit regime | credit leads equity | 10% | |
| H32 UPRO+MA200 | 3x leverage + trend | 25% | vol drag vs trend filter; whipsaw cost brutal at 3x |
| H33 Pullback buy | short-term MR | 5% | |
| H34 SSO TOM+trend | stacked edges | 10% | |

Meta-prior: 0-3 ACCEPTs expected across ~30 tests; any single ACCEPT has ~30-50%
chance of being a multiple-testing artifact → round-2 robustness confirmation required.
The honest expected outcome: leverage-with-trend-armor family (H10/H24/H32) and possibly
overnight-QQQ survive; nearly everything else RA-ONLY or REJECT.
