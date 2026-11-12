"""Momentum strategy on point-in-time S&P 500 members: K-means clusters, then optimised weights.

    python momentum.py                 # build the cached panel if needed, then run the default settings

Every month, among the 150 most liquid stocks that were in the index at the time:
  1. compute technical features, rolling Fama-French betas, past returns and (optionally) three
     momentum predictors;
  2. z-score every feature across stocks on that date and cluster them with K-means, starting from
     centroids seeded at fixed levels of RSI (and, optionally, the momentum predictors), so the
     "momentum" cluster means the same thing every month;
  3. hold the momentum cluster's stocks with positive 12-month returns for the next month, weighted
     by a maximum-Sharpe optimiser (or a less noisy alternative), with turnover costs.

Raw prices, factors and the feature panel are cached in cache/, so the experiments in
experiments.py re-use them instead of downloading 800 tickers each time.
"""
from __future__ import annotations

import math
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import sp500_pit as pit  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)

CONFIG = dict(
    start="2011-06-30",
    end="2026-06-30",
    n_liquid=150,            # the most liquid names per month
    n_clusters=4,
    seed_features=("rsi",),  # features whose centroid values are seeded at fixed levels
    features="base",         # "base" or "extended" (base + the three momentum predictors)
    weights="max_sharpe",    # "max_sharpe", "shrunk_mu", "min_variance", "equal"
    max_weight=0.10,
    cost_bps=10.0,           # per unit of turnover
    seed=0,
    legacy=False,            # True reproduces the run before the 2026-11-11 fixes
)

FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
RETURN_COLS = [f"return_{k}m" for k in (1, 2, 3, 6, 9, 12)]
BASE_FEATURES = ["garman_klass_vol", "rsi", "bb_pctb", "atr", "macd", *RETURN_COLS, *FACTORS]
LEGACY_FEATURES = ["garman_klass_vol", "rsi", "bb_low", "bb_mid", "bb_high", "atr", "macd", *RETURN_COLS, *FACTORS]
# Three published momentum predictors, each an alternative to RSI:
#   mom_12_1        return from 12 months ago to 1 month ago (Jegadeesh-Titman, skipping the reversal month)
#   high_52w        price / its 52-week high (George and Hwang, 2004)
#   mom_6m_risk_adj 6-month return / 6-month volatility (volatility-scaled momentum)
EXTRA_FEATURES = ["mom_12_1", "high_52w", "mom_6m_risk_adj"]


# --------------------------------------------------------------------- data
def _cached(name):
    return os.path.join(CACHE, name)


def load_membership():
    return pit.load_membership(_cached("sp500_membership.csv"))


def download_prices(tickers, cfg):
    path = _cached(f"raw_{cfg['start']}_{cfg['end']}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    import yfinance as yf
    raw = yf.download(tickers, start=pd.Timestamp(cfg["start"]) - pd.DateOffset(months=13), end=cfg["end"],
                      auto_adjust=False, progress=False, threads=True)
    raw = raw.rename(columns={"Adj Close": "adj_close"})
    raw.to_parquet(path)
    return raw


def spy_returns(cfg):
    path = _cached(f"spy_{cfg['start']}_{cfg['end']}.parquet")
    if not os.path.exists(path):
        import yfinance as yf
        s = yf.download("SPY", start=cfg["start"], end=cfg["end"], auto_adjust=False, progress=False)["Adj Close"]
        s = s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
        s.to_frame("spy").to_parquet(path)
    return pd.read_parquet(path)["spy"].pct_change()


def ff_factors(cfg):
    path = _cached("ff5.parquet")
    if not os.path.exists(path):
        from pandas_datareader import data as web
        ff = web.DataReader("F-F_Research_Data_5_Factors_2x3", "famafrench", start="2010-01-01")[0].drop("RF", axis=1)
        ff.index = ff.index.to_timestamp()
        ff = ff.resample("ME").last() / 100
        ff.to_parquet(path)
    return pd.read_parquet(path)


# ----------------------------------------------------------------- features
def rolling_zscore(series, window):
    """Z-score against a trailing window; shift(1) keeps today out of its own mean and std."""
    mean = series.shift(1).rolling(window).mean()
    std = series.shift(1).rolling(window).std()
    return (series - mean) / std


def build_daily_features(raw):
    import pandas_ta
    df = raw.stack(future_stack=True)
    df.index.names = ["date", "ticker"]
    df.columns = df.columns.str.lower()
    df = df.dropna(subset=["adj_close"])

    # Garman-Klass uses only ratios of the same day's prices, so every price must be on one basis.
    # The legacy version mixed the dividend-adjusted close with the unadjusted open (fixed 2026-11-11).
    df["garman_klass_vol"] = (((np.log(df["high"]) - np.log(df["low"])) ** 2) / 2
                              - (2 * np.log(2) - 1) * ((np.log(df["close"]) - np.log(df["open"])) ** 2))
    df["garman_klass_vol_legacy"] = (((np.log(df["high"]) - np.log(df["low"])) ** 2) / 2
                                     - (2 * np.log(2) - 1) * ((np.log(df["adj_close"]) - np.log(df["open"])) ** 2))

    g = df.groupby(level=1)["adj_close"]
    df["rsi"] = g.transform(lambda x: pandas_ta.rsi(close=x, length=20))

    bb = df.groupby(level=1)["adj_close"].apply(lambda x: pandas_ta.bbands(close=np.log1p(x), length=20))
    bb = bb.reset_index(level=0, drop=True)
    keep = [c for c in bb.columns if c.startswith(("BBL", "BBM", "BBU"))][:3]
    bb = bb[keep]
    bb.columns = ["bb_low", "bb_mid", "bb_high"]
    df = df.join(bb)
    # The band LEVELS are log price levels, which just rank stocks by share price across the
    # cross-section. Where the price sits inside its band (%B) is the comparable quantity.
    df["bb_pctb"] = (np.log1p(df["adj_close"]) - df["bb_low"]) / (df["bb_high"] - df["bb_low"])

    def compute_atr(gr, norm_window=126):
        if len(gr) < 14:
            return pd.Series(np.nan, index=gr.index)
        atr = pandas_ta.atr(high=gr["high"], low=gr["low"], close=gr["close"], length=14)
        return pd.Series(np.nan, index=gr.index) if atr is None else rolling_zscore(atr, norm_window)
    df["atr"] = df.groupby(level=1, group_keys=False).apply(compute_atr)

    def compute_macd(close, norm_window=252):
        if len(close.dropna()) < 26:
            return pd.Series(np.nan, index=close.index)
        m = pandas_ta.macd(close=close)
        return pd.Series(np.nan, index=close.index) if m is None or m.empty else rolling_zscore(m.iloc[:, 0], norm_window)
    df["macd"] = df.groupby(level=1, group_keys=False)["adj_close"].apply(compute_macd)

    # the three momentum predictors, from the adjusted close
    df["mom_12_1"] = g.transform(lambda x: x.shift(21) / x.shift(252) - 1)
    df["high_52w"] = g.transform(lambda x: x / x.rolling(252, min_periods=200).max())
    df["mom_6m_risk_adj"] = g.transform(lambda x: (x / x.shift(126) - 1) / (x.pct_change().rolling(126).std() * math.sqrt(252)))

    df["dollar_volume"] = (df["adj_close"] * df["volume"]) / 1e6
    return df


def to_monthly(df, membership, cfg):
    feats = [c for c in df.columns if c not in ["dollar_volume", "volume", "open", "high", "low", "close"]]
    data = pd.concat([
        df.unstack("ticker")["dollar_volume"].resample("ME").mean().stack("ticker", future_stack=True).to_frame("dollar_volume"),
        df.unstack("ticker")[feats].resample("ME").last().stack("ticker", future_stack=True),
    ], axis=1)
    data = data[data.index.get_level_values("date") >= pd.Timestamp(cfg["start"]) - pd.DateOffset(months=13)]
    data = data.dropna(subset=["adj_close", "dollar_volume"])
    # point-in-time membership, applied BEFORE any ranking so non-members are not in the peer group
    dates = data.index.get_level_values("date").unique()
    tickers = data.index.get_level_values("ticker").unique()
    flat = pit.membership_mask(membership, dates, tickers).stack()
    flat.index.names = ["date", "ticker"]
    data = data[flat.reindex(data.index).fillna(False).to_numpy()]
    data["dollar_volume"] = (data["dollar_volume"].unstack("ticker").rolling(5 * 12, min_periods=12).mean().stack())
    data["rank"] = data.groupby("date")["dollar_volume"].rank(ascending=False)
    return data[data["rank"] <= cfg["n_liquid"]].drop(["dollar_volume", "rank"], axis=1)


def add_returns(data):
    """Past 1 to 12-month returns, as monthly geometric averages.

    Outliers are clipped at the 0.5% and 99.5% quantiles ACROSS stocks on each date. The legacy
    version clipped at each stock's own full-history quantiles, which uses future prices.
    """
    out = data.copy()
    for lag in [1, 2, 3, 6, 9, 12]:
        raw = out.groupby(level=1)["adj_close"].pct_change(lag)
        lo = raw.groupby(level="date").transform(lambda x: x.quantile(0.005))
        hi = raw.groupby(level="date").transform(lambda x: x.quantile(0.995))
        out[f"return_{lag}m"] = raw.clip(lo, hi).add(1).pow(1 / lag).sub(1)
        leg = out.groupby(level=1)["adj_close"].pct_change(lag)
        q = leg.groupby(level=1).transform
        out[f"return_{lag}m_legacy"] = leg.clip(q(lambda x: x.quantile(0.005)), q(lambda x: x.quantile(0.995))).add(1).pow(1 / lag).sub(1)
    return out


def add_factor_betas(data, ff):
    import statsmodels.api as sm
    from statsmodels.regression.rolling import RollingOLS
    ff = ff.copy()
    ff.index.name = "date"
    j = ff.join(data["return_1m"]).sort_index().dropna()
    obs = j.groupby(level=1).size()
    j = j[j.index.get_level_values("ticker").isin(obs[obs >= 10].index)]
    betas = j.groupby(level=1, group_keys=False).apply(
        lambda x: RollingOLS(endog=x["return_1m"], exog=sm.add_constant(x.drop("return_1m", axis=1)),
                             window=min(24, x.shape[0]), min_nobs=len(x.columns) + 1).fit(params_only=True).params.drop("const", axis=1))
    lagged = betas.groupby("ticker").shift(1)        # never use a beta fitted with the same month's return
    out = data.join(lagged)
    out[FACTORS] = out.groupby("ticker")[FACTORS].apply(lambda x: x.ffill()).reset_index(level=0, drop=True)
    return out


def build_panel(cfg=CONFIG):
    """Monthly panel with every feature (fixed and legacy versions), cached."""
    path = _cached(f"panel_{cfg['start']}_{cfg['end']}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    membership = load_membership()
    tickers = [t.replace(".", "-") for t in pit.universe_over(membership, cfg["start"], cfg["end"])]
    raw = download_prices(tickers, cfg)
    print(f"downloaded {raw['adj_close'].notna().any().sum()} of {len(tickers)} tickers", flush=True)
    df = build_daily_features(raw)
    data = to_monthly(df, membership, cfg)
    data = add_returns(data)
    data = add_factor_betas(data, ff_factors(cfg))
    data.to_parquet(path)
    return data


def daily_prices(cfg=CONFIG):
    return download_prices(None, cfg)["adj_close"]


# --------------------------------------------------------------- clustering
def feature_list(cfg):
    if cfg["legacy"]:
        return LEGACY_FEATURES
    return BASE_FEATURES + (EXTRA_FEATURES if cfg["features"] == "extended" else [])


def prepare(panel, cfg):
    feats = feature_list(cfg)
    cols = [("garman_klass_vol_legacy" if (cfg["legacy"] and f == "garman_klass_vol") else
             f"{f}_legacy" if (cfg["legacy"] and f in RETURN_COLS) else f) for f in feats]
    d = panel[cols].copy()
    d.columns = feats
    d = d[d.index.get_level_values("date") >= pd.Timestamp(cfg["start"])].replace([np.inf, -np.inf], np.nan).dropna()
    by = d.groupby(level="date")
    if cfg["legacy"]:
        d["rsi"] = by["rsi"].transform(lambda x: (x - x.mean()) / x.std())       # the legacy run scaled RSI only
    else:
        # every feature on the same scale, so no single one (a price level, a volatility) decides the
        # distances K-means works with
        d = by.transform(lambda x: ((x - x.mean()) / x.std()).clip(-5, 5))
    return d


def seed_centroids(feats, cfg):
    k = cfg["n_clusters"]
    c = np.zeros((k, len(feats)))
    levels = np.linspace(-1.5, 1.5, k)            # lowest to highest; the last cluster is "momentum"
    for f in cfg["seed_features"]:
        # a leading "-" seeds the feature the other way round, so the momentum cluster starts LOW on it
        sign, name = (-1.0, f[1:]) if f.startswith("-") else (1.0, f)
        c[:, feats.index(name)] = sign * levels
    return c


def cluster(d, cfg):
    from sklearn.cluster import KMeans
    feats = list(d.columns)
    init = seed_centroids(feats, cfg)

    def one(g):
        g = g.copy()
        if len(g) < cfg["n_clusters"]:
            g["cluster"] = -1
            return g
        g["cluster"] = KMeans(n_clusters=cfg["n_clusters"], init=init, n_init=1,
                              random_state=cfg["seed"]).fit(g[feats]).labels_
        return g
    return d.groupby(level="date", group_keys=False).apply(one)


# --------------------------------------------------------------- weighting
def shrink_mu(rets: pd.DataFrame) -> pd.Series:
    """James-Stein: pull each stock's mean return toward the average of the group.

    A one-year sample mean of daily returns has a standard error about as large as the differences
    between stocks, so most of the spread in raw means is noise. The shrinkage intensity is
    estimated from that standard error: the noisier the means, the closer they are pulled together.
    """
    mu = rets.mean()
    n, t = len(mu), len(rets)
    if n < 4:
        return mu * 252
    se2 = (rets.var() / t).mean()
    spread = ((mu - mu.mean()) ** 2).sum()
    c = min(1.0, (n - 3) * se2 / spread) if spread > 0 else 1.0
    return (mu.mean() + (1 - c) * (mu - mu.mean())) * 252


def optimise(prices, cfg):
    """Weights for one month. Returns (weights, method used): a failed optimiser is counted, not hidden."""
    from pypfopt import risk_models
    from pypfopt.efficient_frontier import EfficientFrontier
    n = prices.shape[1]
    if cfg["weights"] == "equal" or n == 1:
        return {c: 1 / n for c in prices.columns}, "equal"
    rets = prices.pct_change().dropna()
    cov = risk_models.CovarianceShrinkage(prices, frequency=252).ledoit_wolf()
    upper = max(cfg["max_weight"], 1.0 / n + 1e-3)
    ef = EfficientFrontier(None if cfg["weights"] == "min_variance" else
                           (shrink_mu(rets) if cfg["weights"] == "shrunk_mu" else rets.mean() * 252),
                           cov, weight_bounds=(0, upper), solver="SCS")
    try:
        if cfg["weights"] == "min_variance":
            ef.min_volatility()
        else:
            ef.max_sharpe(risk_free_rate=0.0)
        return dict(ef.clean_weights()), cfg["weights"]
    except Exception:  # noqa: BLE001
        return {c: 1 / n for c in prices.columns}, "fallback"


# ----------------------------------------------------------------- back test
def backtest(clusters, px, membership, cfg):
    target = cfg["n_clusters"] - 1
    picks = clusters[clusters["cluster"] == target]
    rets = px.pct_change()
    daily, prev_w, n_exits = [], {}, 0
    methods = {}
    for d in sorted(picks.index.get_level_values("date").unique()):
        members = pit.members_on(membership, d)
        cols = [t for t in picks.xs(d, level=0).index if t in members and t in px.columns]
        if not cols:
            continue
        opt = px.loc[d - pd.DateOffset(months=12):d, cols].dropna(axis=1, how="any")
        if opt.empty:
            continue
        mom = opt.pct_change(min(252, len(opt) - 1)).iloc[-1]
        opt = opt[mom[mom > 0].index.tolist()]
        if opt.shape[1] < 2:
            continue
        w, how = optimise(opt, cfg)
        methods[how] = methods.get(how, 0) + 1
        w = {k: v for k, v in w.items() if v > 1e-6}
        if not w:
            continue
        turnover = sum(abs(w.get(t, 0) - prev_w.get(t, 0)) for t in set(w) | set(prev_w))
        window = rets.loc[d + pd.offsets.BDay(1):d + pd.offsets.MonthEnd(1), list(w)]
        if window.empty:
            continue
        n_exits += int(window.iloc[-1].isna().sum())
        window = window.fillna(0.0)
        port = (window * pd.Series(w)).sum(axis=1)
        port.iloc[0] -= turnover * cfg["cost_bps"] / 1e4
        growth = (1 + window).prod()
        drifted = pd.Series(w) * growth
        prev_w = (drifted / drifted.sum()).to_dict()
        daily.append(port)
    strat = pd.concat(daily).sort_index()
    return strat[~strat.index.duplicated()], {"methods": methods, "mid_hold_exits": n_exits}


def stats(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    down = np.sqrt((np.minimum(r, 0) ** 2).mean())
    return {"CAGR": eq.iloc[-1] ** (1 / yrs) - 1, "Sharpe": r.mean() / r.std() * np.sqrt(252),
            "Sortino": r.mean() / down * np.sqrt(252), "MaxDD": (eq / eq.cummax() - 1).min(),
            "TotalReturn": eq.iloc[-1] - 1}


def evaluate(strat: pd.Series, spy: pd.Series, split="2021-07-01") -> dict:
    """Strategy against SPY over the same days; days the strategy sat out count as cash."""
    bench = spy.loc[strat.index[0]:strat.index[-1]].dropna()
    s = strat.reindex(bench.index).fillna(0.0)
    out = {"strategy": stats(s), "spy": stats(bench)}
    for name, m in (("first_half", s.index < split), ("second_half", s.index >= split)):
        out[name] = {"strategy": stats(s[m]), "spy": stats(bench[m])}
    return out


def run(cfg=CONFIG, panel=None, px=None, spy=None, membership=None):
    cfg = dict(CONFIG, **cfg)
    panel = build_panel(cfg) if panel is None else panel
    px = daily_prices(cfg) if px is None else px
    spy = spy_returns(cfg) if spy is None else spy
    membership = load_membership() if membership is None else membership
    clusters = cluster(prepare(panel, cfg), cfg)
    strat, info = backtest(clusters, px, membership, cfg)
    res = evaluate(strat, spy, cfg.get("split", "2021-07-01"))
    # what the momentum cluster looks like: average raw RSI of its members against everyone
    raw_rsi = panel["rsi"].reindex(clusters.index)
    top = clusters["cluster"] == cfg["n_clusters"] - 1
    info.update({"rsi_momentum_cluster": float(raw_rsi[top].mean()), "rsi_all": float(raw_rsi.mean()),
                 "names_per_month": float(top.groupby(level="date").sum().mean())})
    return res, info, strat


if __name__ == "__main__":
    res, info, _ = run()
    print(pd.DataFrame({k: v for k, v in res.items() if k in ("strategy", "spy")}).round(4).to_string())
    print(info)
