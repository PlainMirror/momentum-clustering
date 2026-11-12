"""Retry the tickers Yahoo returned nothing for, in small batches, and merge them into the cached raw file.

Yahoo sometimes fails live tickers in a large request ("Data doesn't exist"). Delisted ones fail every
time, which is the residual survivorship bias the README reports; this only rescues the transient ones.
"""
import os
import time

import pandas as pd
import yfinance as yf

import momentum as mm
import sp500_pit as pit

cfg = mm.CONFIG
path = mm._cached(f"raw_{cfg['start']}_{cfg['end']}.parquet")
raw = pd.read_parquet(path)
tickers = [t.replace(".", "-") for t in pit.universe_over(mm.load_membership(), cfg["start"], cfg["end"])]
have = raw["adj_close"].notna().any()
missing = [t for t in tickers if t not in have.index or not have.get(t, False)]
print(f"missing before retry: {len(missing)}")
got = []
for i in range(0, len(missing), 20):
    chunk = missing[i:i + 20]
    part = yf.download(chunk, start=pd.Timestamp(cfg["start"]) - pd.DateOffset(months=13), end=cfg["end"],
                       auto_adjust=False, progress=False, threads=False).rename(columns={"Adj Close": "adj_close"})
    if len(part):
        ok = [t for t in chunk if (("adj_close", t) in part.columns) and part[("adj_close", t)].notna().any()]
        got += ok
        if ok:
            raw = raw.drop(columns=[c for c in raw.columns if c[1] in ok], errors="ignore")
            raw = pd.concat([raw, part.loc[:, [c for c in part.columns if c[1] in ok]]], axis=1)
    time.sleep(2)
raw = raw.sort_index(axis=1)
raw.to_parquet(path)
print(f"recovered {len(got)}: {got}")
print(f"now served: {int(raw['adj_close'].notna().any().sum())} of {len(tickers)}")
panel = mm._cached(f"panel_{cfg['start']}_{cfg['end']}.parquet")
if got and os.path.exists(panel):
    os.remove(panel)
    print("panel cache removed; it will be rebuilt")
