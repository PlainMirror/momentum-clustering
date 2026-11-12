"""Does the momentum cluster predict returns? Tested across stocks, not on one portfolio.

    python signal_test.py

The back test gives one return series from about 24 stocks a month, weighted by an optimiser, so
most of its variance is the noise of those few names and the weights. These tests use every stock
in the universe every month, which has far more power, and they ask a sharper question: does the
clustering add anything beyond plain momentum, which is a known factor?

1. Fama-MacBeth. Each month, regress every stock's NEXT-month return on
     - top: 1 if the stock is in the momentum cluster that month,
     - the momentum features themselves (z-scored across stocks that month),
     - controls: last month's return (short-term reversal) and the stock's market beta.
   The average of each monthly coefficient, with a Newey-West t-statistic (3 lags), is the test.
   Specification 2 is the key one: if "top" stays significant with 12-1 momentum in the regression,
   the clustering knows something momentum alone does not.

2. Factor-adjusted portfolio. Each month, equal-weight the momentum cluster, and the cluster minus
   the rest of the universe (long-short). Regress the monthly returns on the Fama-French five
   factors plus the momentum factor (UMD). Alpha that survives UMD is not just the momentum premium.

Both use the clusters of the final version (the three momentum features added), and of the fixed
version for comparison. Returns come from Yahoo adjusted closes, so the residual survivorship bias
described in the README applies here too.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

import momentum as mm

SOURCE = os.environ.get("MOM_DATA", "yahoo")
if SOURCE == "crsp":
    import crsp_data
BASE = dict(crsp_data.CFG) if SOURCE == "crsp" else {}

ROOT = os.path.dirname(os.path.abspath(__file__))
FEATURES = ["mom_12_1", "high_52w", "mom_6m_risk_adj", "rsi"]
SPECS = {
    "1. cluster alone": ["top"],
    "2. cluster + 12-1 momentum": ["top", "mom_12_1"],
    "3. cluster + all momentum features": ["top", "mom_12_1", "high_52w", "mom_6m_risk_adj", "rsi"],
    "4. features alone, no cluster": ["mom_12_1", "high_52w", "mom_6m_risk_adj", "rsi"],
}
CONTROLS = ["return_1m", "Mkt-RF"]


def monthly_returns(px: pd.DataFrame) -> pd.DataFrame:
    """Return from month-end t to month-end t+1, stamped at t. A stock that stops trading inside the
    month has no value for that month (dropped, not set to zero)."""
    m = px.resample("ME").last()
    nxt = m.shift(-1) / m - 1
    alive = px.notna().resample("ME").last().shift(-1).fillna(False).astype(bool)
    return nxt.where(alive)


def umd():
    path = mm._cached("umd.parquet")
    if not os.path.exists(path):
        from pandas_datareader import data as web
        f = web.DataReader("F-F_Momentum_Factor", "famafrench", start="2010-01-01")[0]
        f.columns = ["UMD"]
        f.index = f.index.to_timestamp()
        f = f.resample("ME").last() / 100
        f.to_parquet(path)
    return pd.read_parquet(path)["UMD"]


def build(cfg: dict, panel, px):
    cfg = dict(mm.CONFIG, **BASE, **cfg)
    z = mm.prepare(panel, dict(cfg, features="extended"))            # z-scored features, every row
    cl = mm.cluster(mm.prepare(panel, cfg), cfg)["cluster"]
    d = z[[f for f in FEATURES]].join(panel[CONTROLS]).join(cl, how="inner")
    # controls z-scored across stocks too, so every coefficient is per one cross-sectional sd
    for c in CONTROLS:
        d[c] = d.groupby(level="date")[c].transform(lambda x: (x - x.mean()) / x.std())
    d["top"] = (d["cluster"] == cfg["n_clusters"] - 1).astype(float)
    fwd = monthly_returns(px).stack().rename("fwd")
    fwd.index.names = ["date", "ticker"]
    return d.join(fwd, how="inner").dropna()


def nw_t(series: pd.Series, lags=3):
    fit = sm.OLS(series.to_numpy(), np.ones(len(series))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.params[0]), float(fit.tvalues[0])


def fama_macbeth(d: pd.DataFrame, xs: list) -> pd.DataFrame:
    rows = []
    for date, g in d.groupby(level="date"):
        if len(g) < 30 or g["top"].sum() < 3 and "top" in xs:
            continue
        X = sm.add_constant(g[xs + CONTROLS])
        b = sm.OLS(g["fwd"], X).fit().params
        rows.append(b.rename(date))
    coef = pd.DataFrame(rows)
    out = []
    for c in ["const"] + xs + CONTROLS:
        m, t = nw_t(coef[c])
        out.append({"variable": c, "monthly_%": 100 * m, "annual_%": 1200 * m, "t": t})
    return pd.DataFrame(out), len(coef)


def portfolios(d: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    top = d[d["top"] == 1].groupby(level="date")["fwd"].mean()
    rest = d[d["top"] == 0].groupby(level="date")["fwd"].mean()
    allw = d.groupby(level="date")["fwd"].mean()
    # returns are stamped at formation month t and earned over t+1: line them up with t+1's factors
    series = {"cluster, equal weight, minus T-bill-free universe": top - allw, "cluster minus the rest (long-short)": top - rest}
    out = []
    for name, s in series.items():
        s.index = s.index + pd.offsets.MonthEnd(1)
        j = pd.concat([s.rename("r"), factors], axis=1, join="inner").dropna()
        for label, cols in (("raw mean", []), ("Fama-French 5", mm.FACTORS), ("FF5 + momentum (UMD)", mm.FACTORS + ["UMD"])):
            X = sm.add_constant(j[cols]) if cols else np.ones((len(j), 1))
            fit = sm.OLS(j["r"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
            row = {"portfolio": name, "model": label, "months": len(j),
                   "alpha_annual_%": 1200 * float(fit.params.iloc[0]), "t": float(fit.tvalues.iloc[0])}
            if "UMD" in cols:
                row["UMD_loading"] = float(fit.params["UMD"])
                row["UMD_t"] = float(fit.tvalues["UMD"])
            out.append(row)
    return pd.DataFrame(out)


def main():
    if SOURCE == "crsp":
        panel, px = crsp_data.build(), crsp_data.daily_index(set())
        factors = crsp_data.ff_long().join(crsp_data.umd_long(), how="inner")
    else:
        panel, px = mm.build_panel(), mm.daily_prices()
        factors = mm.ff_factors(mm.CONFIG).join(umd(), how="inner")
    lines = [f"# Signal tests ({SOURCE})\n"]
    for name, cfg in (("final (three momentum features added)", {"features": "extended"}), ("fixed", {})):
        d = build(cfg, panel, px)
        months = d.index.get_level_values("date")
        head = (f"## {name}\n\n{len(d):,} stock-months, {months.nunique()} months "
                f"({months.min().date()} to {months.max().date()}), {d['top'].mean() * 100:.1f}% of them in the cluster.\n")
        print(head, flush=True)
        lines.append(head)
        for spec, xs in SPECS.items():
            if name.startswith("fixed") and spec.startswith("4."):
                continue
            t, n = fama_macbeth(d, xs)
            print(f"{spec}  ({n} monthly regressions)\n{t.round(3).to_string(index=False)}\n", flush=True)
            lines += [f"### Fama-MacBeth {spec} ({n} months)\n", t.round(3).to_markdown(index=False) if hasattr(t, "to_markdown") and False else
                      "| " + " | ".join(t.columns) + " |\n|" + "---|" * len(t.columns) + "\n" +
                      "\n".join("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r) + " |" for r in t.itertuples(index=False)), ""]
        p = portfolios(d, factors)
        print(p.round(3).to_string(index=False), "\n", flush=True)
        lines += ["### Factor-adjusted portfolios\n", "| " + " | ".join(p.columns) + " |\n|" + "---|" * len(p.columns) + "\n" +
                  "\n".join("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r) + " |" for r in p.itertuples(index=False)), ""]
    with open(os.path.join(ROOT, "results", f"signal_test{'_crsp' if SOURCE == 'crsp' else ''}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote results/signal_test.md")


if __name__ == "__main__":
    main()
