"""A cluster rebuilt around 12-1 momentum, chosen on CRSP 1999-2022, then tested ONCE on 2023-2026.

    python holdout.py

Why: on CRSP, 12-1 month momentum predicts higher returns across stocks (t = 2.2) and 20-day RSI
predicts LOWER ones (t = -3.0), yet the clusters were seeded on high RSI. These designs seed the
momentum cluster on high 12-1 momentum instead, and on LOW RSI (strong long-run trend, short-term
pullback). Everything below was fixed before any of it ran.

Step 1, choose on CRSP (1999-2022, halves split at 2011). Three candidates, all with the extended
features and 4 clusters:
    M1  seeded on 12-1 momentum only
    M2  seeded on 12-1 momentum, and RSI the other way round
    M3  seeded on 12-1 momentum and the 52-week high, and RSI the other way round
A candidate qualifies only if its Sharpe beats CRSP's fixed version in BOTH halves. Of those that
qualify, the one whose worse half is best is chosen. If none qualifies, there is no holdout test.

Step 2, test once on data none of the CRSP work used: Yahoo, January 2023 to June 2026, the S&P 500
point-in-time universe. The chosen design is compared with SPY, and with the two designs the
2013-2026 Yahoo study had picked (fixed and extended), which were chosen on data that included
these years, so they are not a fair holdout and are shown for reference only.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

import crsp_data as cd
import momentum as mm

ROOT = os.path.dirname(os.path.abspath(__file__))
HOLD_START, HOLD_END = "2023-01-01", "2026-06-30"
CANDIDATES = {
    "M1 seeded on 12-1 momentum": {"features": "extended", "seed_features": ("mom_12_1",)},
    "M2 + RSI the other way": {"features": "extended", "seed_features": ("mom_12_1", "-rsi")},
    "M3 + 52-week high, RSI the other way": {"features": "extended", "seed_features": ("mom_12_1", "high_52w", "-rsi")},
}


def alpha(strat: pd.Series, spy: pd.Series):
    b = spy.loc[strat.index[0]:strat.index[-1]].dropna()
    x = strat.reindex(b.index).fillna(0.0)
    o = sm.OLS(x, sm.add_constant(b)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    return 252 * 100 * float(o.params.iloc[0]), float(o.tvalues.iloc[0]), float(o.params.iloc[1])


def row(name, strat, spy, split=None):
    s = mm.stats(strat.reindex(spy.loc[strat.index[0]:strat.index[-1]].dropna().index).fillna(0.0))
    a, t, beta = alpha(strat, spy)
    r = {"design": name, "Sharpe": s["Sharpe"], "CAGR_%": 100 * s["CAGR"], "MaxDD_%": 100 * s["MaxDD"],
         "total_%": 100 * s["TotalReturn"], "alpha_%": a, "alpha_t": t, "beta": beta}
    if split:
        x = strat.reindex(spy.loc[strat.index[0]:strat.index[-1]].dropna().index).fillna(0.0)
        r["Sharpe_1"] = mm.stats(x[x.index < split])["Sharpe"]
        r["Sharpe_2"] = mm.stats(x[x.index >= split])["Sharpe"]
    return r


def main():
    lines = ["# Holdout test\n"]
    # ---- step 1: CRSP
    d = cd.data_bundle()
    rows = []
    for name, ch in {"fixed (reference)": {}, **CANDIDATES}.items():
        _, info, s = mm.run(dict(cd.CFG, **ch), **d)
        r = row(name, s, d["spy"], cd.CFG["split"])
        r["names_per_month"] = info["names_per_month"]
        r["rsi_of_cluster"] = info["rsi_momentum_cluster"]
        rows.append(r)
        print(r, flush=True)
    crsp = pd.DataFrame(rows)
    base = crsp.iloc[0]
    crsp["qualifies"] = (crsp["Sharpe_1"] > base["Sharpe_1"]) & (crsp["Sharpe_2"] > base["Sharpe_2"])
    crsp.loc[0, "qualifies"] = False
    q = crsp[crsp["qualifies"]]
    lines += ["## Step 1: choose on CRSP, 1999-2022 (halves split at 2011)\n", md(crsp), ""]
    if not len(q):
        lines.append("No candidate beats the fixed version in both halves, so there is no holdout test.")
        print(lines[-1])
        save(lines, crsp, None)
        return
    chosen = q.loc[q[["Sharpe_1", "Sharpe_2"]].min(axis=1).idxmax(), "design"]
    lines.append(f"Chosen: **{chosen}**\n")
    print("chosen:", chosen, flush=True)

    # ---- step 2: Yahoo holdout, run once
    y = dict(panel=mm.build_panel(), px=mm.daily_prices(), spy=mm.spy_returns(mm.CONFIG), membership=mm.load_membership())
    spy_h = y["spy"].loc[HOLD_START:HOLD_END]
    hold = []
    for name, ch in {chosen: CANDIDATES[chosen], "fixed (picked on 2013-26, reference)": {},
                     "extended (picked on 2013-26, reference)": {"features": "extended"}}.items():
        _, _, s = mm.run(ch, **y)
        hold.append(row(name, s.loc[HOLD_START:HOLD_END], spy_h))
    sp = mm.stats(spy_h.dropna())
    hold.append({"design": "SPY", "Sharpe": sp["Sharpe"], "CAGR_%": 100 * sp["CAGR"], "MaxDD_%": 100 * sp["MaxDD"],
                 "total_%": 100 * sp["TotalReturn"]})
    ho = pd.DataFrame(hold)
    print(ho.round(3).to_string(index=False), flush=True)
    lines += [f"## Step 2: the holdout, Yahoo {HOLD_START} to {HOLD_END}, run once\n", md(ho), ""]
    save(lines, crsp, ho)


def md(df):
    f = df.copy()
    head = "| " + " | ".join(f.columns) + " |\n|" + "---|" * len(f.columns)
    body = ["| " + " | ".join(f"{v:.2f}" if isinstance(v, (float, np.floating)) else str(v) for v in r) + " |"
            for r in f.itertuples(index=False)]
    return "\n".join([head] + body)


def save(lines, crsp, ho):
    with open(os.path.join(ROOT, "results", "holdout.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    crsp.to_csv(os.path.join(ROOT, "results", "holdout_crsp.csv"), index=False)
    if ho is not None:
        ho.to_csv(os.path.join(ROOT, "results", "holdout_yahoo.csv"), index=False)
    print("wrote results/holdout.md")


if __name__ == "__main__":
    main()
