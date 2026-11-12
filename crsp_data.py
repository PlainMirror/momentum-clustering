"""The same panel as momentum.build_panel, built from CRSP instead of Yahoo, for 1997 to 2022.

    python crsp_data.py      # builds cache/crsp_panel.parquet and the files the back test needs

CRSP keeps every stock until it actually stops trading, so firms that went bankrupt or were bought
stay in the universe for as long as they existed. That closes the survivorship gap Yahoo leaves
(200 of 822 historical members missing). Three differences from the Yahoo version:

  * The universe is the 500 largest US stocks by market cap each month, not the S&P 500 list. The
    course files that carry tickers cover only some industries, so the S&P 500 list (which is by
    ticker) can't be matched to CRSP reliably: UNH, COST, NVDA and GS were all missing. The top 500
    by market cap is the usual stand-in in academic work, and it is free of survivorship bias by
    construction. Exchange-traded funds (SIC 6726) are left out; a few large foreign ADRs can enter.
    The 150 names traded are the largest 150, since the daily file has no volume.

  * CRSP here has daily RETURNS but no daily open, high or low. So "garman_klass_vol" is replaced by
    20-day realised variance and "atr" by the 14-day mean absolute return (z-scored against its own
    past, as ATR was). The column names are kept so the clustering code is unchanged.
  * The daily file has no separate delisting returns, so a stock that delists drops out at its last
    trading price. That still understates bankruptcies, but far less than leaving them out entirely.

The CRSP files are licensed course data (MGT 8803) and stay out of the repository; only results go in.
Point CRSP_DIR at the folder that holds them.
"""
from __future__ import annotations

import glob
import math
import os

import numpy as np
import pandas as pd

import momentum as mm
import sp500_pit as pit

AIFF = os.environ.get("CRSP_DIR", r"C:\Narender\Ai For Finance")
MONTH_END = os.path.join(AIFF, "Assignment 2.1 Monetary Policy Reactions", "_cache", "month_end.parquet")
DAILY = os.path.join(AIFF, "Assignment 2.1 Monetary Policy Reactions", "_cache", "daily_ret")
CFG = dict(start="1997-01-01", end="2022-12-31", split="2011-01-01")


def c(name):
    return mm._cached(name)


# ---------------------------------------------------------------- universe
def market_caps() -> pd.DataFrame:
    """Month-end market cap of every CRSP security except exchange-traded funds."""
    d = pd.read_parquet(MONTH_END)
    d = d[(d["SICCD"] != 6726) & d["PRC"].notna() & (d["SHROUT"] > 0)].copy()
    d["date"] = d["date"] + pd.offsets.MonthEnd(0)
    d["mcap"] = d["PRC"].abs() * d["SHROUT"]
    lo, hi = pd.Timestamp(CFG["start"]) - pd.DateOffset(years=1), pd.Timestamp(CFG["end"])
    d = d[(d["date"] >= lo) & (d["date"] <= hi)]
    d["ticker"] = d["PERMNO"].astype(str)
    return d[["date", "ticker", "mcap"]]


def top500_membership(caps: pd.DataFrame) -> pd.Series:
    """Date -> frozenset of the 500 largest stocks that month (same format as sp500_pit)."""
    caps = caps.assign(rank=caps.groupby("date")["mcap"].rank(ascending=False))
    top = caps[caps["rank"] <= 500]
    return top.groupby("date")["ticker"].apply(frozenset).sort_index()


# ----------------------------------------------------------------- returns
def daily_index(permnos: set) -> pd.DataFrame:
    """Total-return index per PERMNO (1 on its first day), NaN outside the days it traded."""
    path = c("crsp_px.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    keep = {int(p) for p in permnos}
    frames = []
    for f in sorted(glob.glob(os.path.join(DAILY, "*.parquet"))):
        y = int(os.path.basename(f)[:4])
        if y < int(CFG["start"][:4]) - 1 or y > int(CFG["end"][:4]):
            continue
        d = pd.read_parquet(f)
        frames.append(d[d["PERMNO"].isin(keep)])
    r = pd.concat(frames).pivot(index="date", columns="PERMNO", values="RET").astype(float).sort_index()
    r.columns = [str(c_) for c_ in r.columns]
    idx = (1 + r.fillna(0)).cumprod()
    first, last = r.apply(pd.Series.first_valid_index), r.apply(pd.Series.last_valid_index)
    dates = r.index.to_numpy()
    for col in idx.columns:
        idx.loc[(dates < first[col]) | (dates > last[col]), col] = np.nan
    idx.to_parquet(path)
    return idx


# ---------------------------------------------------------------- features
def daily_features(px: pd.DataFrame) -> pd.DataFrame:
    import pandas_ta
    rows = []
    for col in px.columns:
        x = px[col].dropna()
        if len(x) < 60:
            continue
        r = x.pct_change()
        f = pd.DataFrame(index=x.index)
        f["adj_close"] = x
        f["garman_klass_vol"] = (r ** 2).rolling(20).mean()                          # realised variance
        f["rsi"] = pandas_ta.rsi(close=x, length=20)
        bb = pandas_ta.bbands(close=np.log1p(x), length=20)
        if bb is not None:
            lo, hi = bb.filter(like="BBL").iloc[:, 0], bb.filter(like="BBU").iloc[:, 0]
            f["bb_pctb"] = (np.log1p(x) - lo) / (hi - lo)
        f["atr"] = mm.rolling_zscore(r.abs().rolling(14).mean(), 126)                # true-range proxy
        mac = pandas_ta.macd(close=x)
        if mac is not None and not mac.empty:
            f["macd"] = mm.rolling_zscore(mac.iloc[:, 0], 252)
        f["mom_12_1"] = x.shift(21) / x.shift(252) - 1
        f["high_52w"] = x / x.rolling(252, min_periods=200).max()
        f["mom_6m_risk_adj"] = (x / x.shift(126) - 1) / (r.rolling(126).std() * math.sqrt(252))
        mon = f.resample("ME").last()
        mon["ticker"] = col
        rows.append(mon)
    out = pd.concat(rows).reset_index().rename(columns={"index": "date"}).set_index(["date", "ticker"])
    return out


def build(cfg=CFG):
    path = c("crsp_panel.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    caps = market_caps()
    mem = top500_membership(caps)
    everyone = set().union(*mem.values)
    print(f"top-500 universe: {len(everyone)} distinct stocks over {len(mem)} months", flush=True)
    mem.apply(lambda s: ",".join(sorted(s))).rename("tickers").rename_axis("date").to_csv(c("crsp_membership.csv"))
    px = daily_index(everyone)
    print(f"daily returns: {px.shape[1]} stocks, {px.index[0].date()} to {px.index[-1].date()}", flush=True)
    data = daily_features(px)
    # size ranks the names here (the daily file has no volume); the column keeps its old name
    dv = caps.set_index(["date", "ticker"])["mcap"].rename("dollar_volume")
    data = data.join(dv, how="inner")
    data = data[data.index.get_level_values("date") >= pd.Timestamp(cfg["start"])]
    # point-in-time membership BEFORE ranking, as in the Yahoo version
    dates = data.index.get_level_values("date").unique()
    flat = pit.membership_mask(mem, dates, data.index.get_level_values("ticker").unique()).stack()
    flat.index.names = ["date", "ticker"]
    data = data[flat.reindex(data.index).fillna(False).to_numpy()]
    data["rank"] = data.groupby("date")["dollar_volume"].rank(ascending=False)
    data = data[data["rank"] <= mm.CONFIG["n_liquid"]].drop(["dollar_volume", "rank"], axis=1)
    data = mm.add_returns(data)
    data = mm.add_factor_betas(data, ff_long())
    data.to_parquet(path)
    return data


def ff_long():
    path = c("ff5_1995.parquet")
    if not os.path.exists(path):
        from pandas_datareader import data as web
        ff = web.DataReader("F-F_Research_Data_5_Factors_2x3", "famafrench", start="1995-01-01")[0].drop("RF", axis=1)
        ff.index = ff.index.to_timestamp()
        (ff.resample("ME").last() / 100).to_parquet(path)
    return pd.read_parquet(path)


def umd_long():
    path = c("umd_1995.parquet")
    if not os.path.exists(path):
        from pandas_datareader import data as web
        f = web.DataReader("F-F_Momentum_Factor", "famafrench", start="1995-01-01")[0]
        f.columns = ["UMD"]
        f.index = f.index.to_timestamp()
        (f.resample("ME").last() / 100).to_parquet(path)
    return pd.read_parquet(path)["UMD"]


def membership():
    return pit.load_membership(c("crsp_membership.csv"))


def data_bundle():
    return dict(panel=build(), px=daily_index(set()), spy=mm.spy_returns(dict(mm.CONFIG, **CFG)), membership=membership())


if __name__ == "__main__":
    import time
    t = time.time()
    p = build()
    print(p.shape, f"{time.time() - t:.0f}s", p.index.get_level_values("date").min().date(), p.index.get_level_values("date").max().date())
