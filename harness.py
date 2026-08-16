"""Backtest harness. All series are pandas Series/DataFrames indexed by Date."""
import os
import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

COST_BPS = {
    "spy": 1.0, "qqq": 1.0, "iwm": 1.0, "dia": 1.0, "tlt": 1.0, "ief": 1.0,
    "shy": 1.0, "agg": 1.0, "gld": 1.0,
    "xlk": 2.5, "xlf": 2.5, "xle": 2.5, "xlv": 2.5, "xli": 2.5, "xlp": 2.5,
    "xlu": 2.5, "xly": 2.5, "xlb": 2.5, "efa": 2.5, "eem": 2.5, "vnq": 2.5,
    "lqd": 2.5, "hyg": 2.5, "vug": 2.5, "vtv": 2.5,
    "mtum": 3.0, "vlue": 3.0, "qual": 3.0, "usmv": 3.0, "splv": 3.0,
    "sphb": 3.0, "ijs": 3.0, "sso": 3.0, "upro": 3.0,
}
FIN_SPREAD_ANN = 0.005  # financing spread over cash for leverage
BORROW_FEE_ANN = 0.0025  # stock-borrow fee for shorts (easy-to-borrow large caps/ETFs)


def load(sym):
    """Load a stooq csv. sym like 'spy.us' or 'spx' (indices saved without ^)."""
    path = os.path.join(DATA, f"{sym}.csv")
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def close(sym):
    return load(sym)["Close"].rename(sym)


def cost_of(sym):
    base = sym.split(".")[0]
    return COST_BPS.get(base, 3.0) / 1e4


def single_asset_strategy(pos, asset_close, cash_ret=None, cost=None, sym=None):
    """pos[t] decided at close t -> earns asset return t+1. Returns net daily returns.
    pos may be in [0, 2]; cash remainder earns cash_ret; leverage pays cash+spread."""
    r = asset_close.pct_change()
    if cost is None:
        cost = cost_of(sym or asset_close.name)
    pos = pos.reindex(r.index).ffill().fillna(0.0)
    held = pos.shift(1).fillna(0.0)
    if cash_ret is None:
        cash_ret = pd.Series(0.0, index=r.index)
    cash_ret = cash_ret.reindex(r.index).fillna(0.0)
    # cash on the unspent long fraction (shorts: NAV stays in cash, no rebate on proceeds)
    long_cash = (1 - held.clip(lower=0)).clip(lower=0)
    borrow = (held - 1).clip(lower=0)
    short_fee = (-held).clip(lower=0) * BORROW_FEE_ANN / 252
    fin_daily = cash_ret + FIN_SPREAD_ANN / 252
    tc = cost * pos.diff().abs().fillna(0.0)
    sr = held * r + long_cash * cash_ret - borrow * fin_daily - short_fee - tc
    return sr.dropna()


def multi_asset_strategy(weights, closes, cash_ret=None, costs=None):
    """weights: DataFrame (dates x assets), decided at close t. closes: DataFrame."""
    R = closes.pct_change()
    W = weights.reindex(R.index).ffill().fillna(0.0)
    held = W.shift(1).fillna(0.0)
    if cash_ret is None:
        cash_ret = pd.Series(0.0, index=R.index)
    cash_ret = cash_ret.reindex(R.index).fillna(0.0)
    if costs is None:
        costs = {c: cost_of(c) for c in closes.columns}
    tc = sum(costs[c] * W[c].diff().abs().fillna(0.0) for c in W.columns)
    gross = (held * R).sum(axis=1)
    exposure = held.sum(axis=1)
    resid = (1 - exposure).clip(lower=0)
    borrow = (exposure - 1).clip(lower=0)
    fin_daily = cash_ret + FIN_SPREAD_ANN / 252
    sr = gross + resid * cash_ret - borrow * fin_daily - tc
    return sr.dropna()


def stats(strat_ret, bench_ret, name=""):
    df = pd.concat([strat_ret.rename("s"), bench_ret.rename("b")], axis=1, join="inner").dropna()
    s, b = df["s"], df["b"]
    n = len(s)
    if n < 252:
        return {"name": name, "n_days": n, "note": "TOO SHORT"}
    yrs = n / 252.0
    cs, cb = (1 + s).cumprod(), (1 + b).cumprod()
    cagr = cs.iloc[-1] ** (1 / yrs) - 1
    bcagr = cb.iloc[-1] ** (1 / yrs) - 1
    vol = s.std() * np.sqrt(252)
    sharpe = s.mean() / s.std() * np.sqrt(252) if s.std() > 0 else np.nan
    bsharpe = b.mean() / b.std() * np.sqrt(252)
    ex = s - b
    t = ex.mean() / ex.std() * np.sqrt(n) if ex.std() > 0 else np.nan
    half = n // 2
    ex1 = (1 + s.iloc[:half]).prod() / (1 + b.iloc[:half]).prod() - 1
    ex2 = (1 + s.iloc[half:]).prod() / (1 + b.iloc[half:]).prod() - 1
    r12s = cs / cs.shift(252) - 1
    r12b = cb / cb.shift(252) - 1
    mask = r12s.notna() & r12b.notna()
    win12 = (r12s[mask] > r12b[mask]).mean() if mask.any() else np.nan
    dd = (cs / cs.cummax() - 1).min()
    bdd = (cb / cb.cummax() - 1).min()
    accept = (cagr > bcagr) and (ex1 > 0) and (ex2 > 0) and (t >= 1.5) and (win12 >= 0.55)
    ra_only = (not accept) and (sharpe - bsharpe >= 0.15)
    verdict = "ACCEPT" if accept else ("RA-ONLY" if ra_only else "REJECT")
    return {
        "name": name, "start": str(s.index[0].date()), "end": str(s.index[-1].date()),
        "n_days": n, "cagr": cagr, "bench_cagr": bcagr, "excess_cagr": cagr - bcagr,
        "vol": vol, "sharpe": sharpe, "bench_sharpe": bsharpe, "maxdd": dd,
        "bench_maxdd": bdd, "t_excess": t, "half1_ex": ex1, "half2_ex": ex2,
        "win12": win12, "verdict": verdict,
    }


def fmt_table(rows):
    cols = ["name", "start", "end", "cagr", "bench_cagr", "excess_cagr", "sharpe",
            "bench_sharpe", "maxdd", "t_excess", "half1_ex", "half2_ex", "win12", "verdict"]
    out = []
    hdr = f"{'name':<26}{'start':<11}{'end':<11}{'cagr':>7}{'bench':>7}{'exc':>7}" \
          f"{'shp':>6}{'bshp':>6}{'mdd':>7}{'t':>6}{'h1ex':>8}{'h2ex':>8}{'w12':>6}  verdict"
    out.append(hdr)
    out.append("-" * len(hdr))
    for r in rows:
        if r.get("note") == "TOO SHORT":
            out.append(f"{r['name']:<26} TOO SHORT (n={r['n_days']})")
            continue
        out.append(
            f"{r['name']:<26}{r['start']:<11}{r['end']:<11}"
            f"{r['cagr']*100:>6.1f}%{r['bench_cagr']*100:>6.1f}%{r['excess_cagr']*100:>6.1f}%"
            f"{r['sharpe']:>6.2f}{r['bench_sharpe']:>6.2f}{r['maxdd']*100:>6.1f}%"
            f"{r['t_excess']:>6.2f}{r['half1_ex']*100:>7.1f}%{r['half2_ex']*100:>7.1f}%"
            f"{r['win12']*100:>5.0f}%  {r['verdict']}"
        )
    return "\n".join(out)


def rsi(closes, period=2):
    d = closes.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    ru = up.ewm(alpha=1.0 / period, adjust=False).mean()
    rd = dn.ewm(alpha=1.0 / period, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd)


def month_end_mask(idx):
    ser = pd.Series(idx, index=idx)
    return ser.groupby(idx.to_period("M")).transform("max") == ser


def turn_of_month_mask(idx, days_before=4, days_after=3):
    per = idx.to_period("M")
    g = pd.Series(np.arange(len(idx)), index=idx)
    from_start = g.groupby(per).cumcount() + 1
    from_end = g.iloc[::-1].groupby(per[::-1]).cumcount().iloc[::-1] + 1
    return (from_end <= days_before) | (from_start <= days_after)
