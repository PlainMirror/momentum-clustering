"""Which of the four ideas to keep, decided by a rule fixed before any of them ran.

    python experiments.py

Every variant changes ONE thing from the fixed baseline. Results are split at 2021-07-01 into two
halves: July 2013 to June 2021 and July 2021 to June 2026.

    THE RULE: a change is kept only if the strategy's Sharpe ratio is higher than the fixed
    baseline's in BOTH halves.

If more than one K, or more than one weighting, passes, the one whose worse half is best is used.
The new features are used seeded if the seeded version passes, unseeded if only that passes. The
kept changes are then combined and the combination is reported for both halves as well.

Variants (written down before the first run):
    legacy        the run before the 2026-11-11 fixes, for reference only
    fixed         the bug fixes: Garman-Klass on one price basis, Bollinger %B instead of band levels,
                  every feature z-scored before K-means, outliers clipped across stocks not across time
    K = 5, 6, 8   more clusters; RSI seeds spread evenly from -1.5 to +1.5, the top one is "momentum"
    shrunk_mu     James-Stein shrinkage of the expected returns fed to the max-Sharpe optimiser
    min_variance  no expected returns at all: minimum variance within the momentum cluster
    equal         equal weights within the momentum cluster
    extended      three more features (12-1 month momentum, distance to 52-week high,
                  volatility-scaled 6-month momentum), not seeded
    seeded        the same three, also seeded in the centroids at the same levels as RSI
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

import momentum as mm

# MOM_DATA=crsp runs the same experiments on CRSP, 1997 to 2022, split at 2011 (see crsp_data.py)
SOURCE = os.environ.get("MOM_DATA", "yahoo")
if SOURCE == "crsp":
    import crsp_data
    BASE = dict(crsp_data.CFG)
    HALVES = ("Sharpe 1999-2010", "Sharpe 2011-22")
    SUFFIX = "_crsp"
else:
    BASE = {}
    HALVES = ("Sharpe 2013-21", "Sharpe 2021-26")
    SUFFIX = ""

ROOT = os.path.dirname(os.path.abspath(__file__))
SEEDED = ("rsi", "mom_12_1", "high_52w", "mom_6m_risk_adj")
VARIANTS = {
    "legacy": {"legacy": True},
    "fixed": {},
    "K = 5": {"n_clusters": 5},
    "K = 6": {"n_clusters": 6},
    "K = 8": {"n_clusters": 8},
    "shrunk_mu": {"weights": "shrunk_mu"},
    "min_variance": {"weights": "min_variance"},
    "equal": {"weights": "equal"},
    "extended": {"features": "extended"},
    "seeded": {"features": "extended", "seed_features": SEEDED},
}
GROUPS = {"K": ["K = 5", "K = 6", "K = 8"], "weights": ["shrunk_mu", "min_variance", "equal"],
          "features": ["seeded", "extended"]}

_cache = {}


def _data():
    if not _cache:
        if SOURCE == "crsp":
            _cache.update(crsp_data.data_bundle())
        else:
            _cache.update(panel=mm.build_panel(), px=mm.daily_prices(), spy=mm.spy_returns(mm.CONFIG),
                          membership=mm.load_membership())
    return _cache


def run_one(item):
    name, change = item
    d = _data()
    res, info, strat = mm.run(dict(BASE, **change), **d)
    row = {"variant": name}
    for part in ("strategy", "first_half", "second_half"):
        s = res[part] if part == "strategy" else res[part]["strategy"]
        for k, v in s.items():
            row[f"{part}_{k}"] = v
    for k, v in res["spy"].items():
        row[f"spy_{k}"] = v
    row["spy_first_Sharpe"] = res["first_half"]["spy"]["Sharpe"]
    row["spy_second_Sharpe"] = res["second_half"]["spy"]["Sharpe"]
    row.update({"names_per_month": info["names_per_month"], "rsi_momentum_cluster": info["rsi_momentum_cluster"],
                "rsi_all": info["rsi_all"], "optimiser": json.dumps(info["methods"]), "start": str(strat.index[0].date()),
                "end": str(strat.index[-1].date())})
    return row


def table(rows: pd.DataFrame) -> str:
    cols = {"variant": "Variant", "first_half_Sharpe": HALVES[0], "second_half_Sharpe": HALVES[1],
            "strategy_Sharpe": "Sharpe", "strategy_CAGR": "CAGR", "strategy_MaxDD": "Max DD",
            "names_per_month": "Names a month", "rsi_momentum_cluster": "RSI of cluster", "kept": "Kept"}
    t = rows[[c for c in cols if c in rows]].rename(columns=cols).copy()
    for c in ("CAGR", "Max DD"):
        t[c] = (100 * t[c]).round(1).astype(str) + "%"
    for c in (*HALVES, "Sharpe"):
        t[c] = t[c].round(2)
    t["Names a month"] = t["Names a month"].round(1)
    t["RSI of cluster"] = t["RSI of cluster"].round(1)
    head = "| " + " | ".join(t.columns) + " |\n|" + "---|" * len(t.columns)
    return "\n".join([head] + ["| " + " | ".join(str(v) for v in r) + " |" for r in t.itertuples(index=False)])


def main():
    _data()          # build every cache file once here, so parallel workers only ever read them
    workers = max(1, min(len(VARIANTS), (os.cpu_count() or 4) - 2))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        todo = {k: v for k, v in VARIANTS.items() if not (SOURCE == "crsp" and k == "legacy")}
        rows = pd.DataFrame(list(pool.map(run_one, todo.items())))
    base = rows.set_index("variant").loc["fixed"]
    rows["kept"] = [(v not in ("legacy", "fixed")) and r.first_half_Sharpe > base.first_half_Sharpe
                    and r.second_half_Sharpe > base.second_half_Sharpe for v, r in zip(rows["variant"], rows.itertuples())]
    final = {}
    for g, names in GROUPS.items():
        ok = rows[rows["variant"].isin(names) & rows["kept"]]
        if not len(ok):
            continue
        if g == "features":
            pick = "seeded" if "seeded" in set(ok["variant"]) else "extended"
        else:
            pick = ok.loc[ok[["first_half_Sharpe", "second_half_Sharpe"]].min(axis=1).idxmax(), "variant"]
        final.update(VARIANTS[pick])
    print(rows[["variant", "first_half_Sharpe", "second_half_Sharpe", "strategy_Sharpe", "strategy_CAGR",
                "strategy_MaxDD", "names_per_month", "rsi_momentum_cluster", "optimiser", "kept"]].round(3).to_string(index=False), flush=True)
    print(f"final changes: {final}", flush=True)
    out = [rows]
    if final:
        out.append(pd.DataFrame([run_one(("final", final))]).assign(kept=None))
    allr = pd.concat(out, ignore_index=True)
    allr.to_csv(os.path.join(ROOT, "results", f"experiments{SUFFIX}.csv"), index=False)
    b = allr.iloc[0]
    md = [f"# Momentum experiments ({SOURCE})\n\nBack test {b['start']} to {b['end']}, split at {BASE.get('split', '2021-07-01')}. "
          f"SPY over the same days: Sharpe {b['spy_Sharpe']:.2f} ({HALVES[0][7:]} {b['spy_first_Sharpe']:.2f}, "
          f"{HALVES[1][7:]} {b['spy_second_Sharpe']:.2f}), CAGR {100 * b['spy_CAGR']:.1f}%, max drawdown {100 * b['spy_MaxDD']:.1f}%.\n",
          table(allr), "", f"Final changes: `{final}`"]
    with open(os.path.join(ROOT, "results", f"experiments{SUFFIX}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
