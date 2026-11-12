"""
sp500_pit.py
============
Point-in-time S&P 500 index membership.

WHY THIS EXISTS
---------------
Scraping the current constituent list from Wikipedia and pulling N years of
history for those tickers introduces TWO distinct biases:

  1. SURVIVORSHIP BIAS - firms that were in the index and later left
     (bankruptcy, acquisition, removal for underperformance) never appear.
     The universe is pre-filtered for having survived.

  2. INDEX-INCLUSION / BACKFILL BIAS - a firm added to the index in 2021 has
     its 2011-2021 history included as if it were investable the whole time.
     Firms are added AFTER strong runs, so this systematically imports the
     best years of the best performers. For a momentum strategy this is
     usually the LARGER of the two effects.

This module supplies the membership calendar needed to remove both.

DATA SOURCE
-----------
fja05680/sp500 on GitHub, which merges Andreas Clenow's 1996-2019 list
(from `Trading Evolved`) with hand-maintained changes since. Roughly 497
members per date, 1996 to present.

Caveat worth knowing: the maintainer flags the first ~5 years (1996-2001) as
possibly missing symbols. Start backtests at 2001 or later if that matters.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

_REPO = "https://raw.githubusercontent.com/fja05680/sp500/master/"
_FILE = "S&P 500 Historical Components & Changes (Updated).csv"
URL = _REPO + urllib.parse.quote(_FILE)


def load_membership(cache: str | Path = "sp500_membership.csv") -> pd.Series:
    """Download (once) and return a Series: date -> frozenset of tickers.

    The file is ~5MB. It is cached locally so repeat runs are offline.
    """
    cache = Path(cache)
    if not cache.exists():
        print(f"Downloading point-in-time membership -> {cache}")
        urllib.request.urlretrieve(URL, cache)

    raw = pd.read_csv(cache)
    raw["date"] = pd.to_datetime(raw["date"])
    s = raw.set_index("date")["tickers"].apply(
        lambda x: frozenset(t.strip() for t in str(x).split(",") if t.strip())
    )
    return s.sort_index()


def members_on(membership: pd.Series, when) -> frozenset:
    """Members as of `when`, using the most recent snapshot at or before it.

    Snapshots exist only on change dates, so an as-of lookup is required --
    indexing by exact date would miss almost every query.
    """
    when = pd.Timestamp(when)
    idx = membership.index.searchsorted(when, side="right") - 1
    if idx < 0:
        raise KeyError(f"{when.date()} precedes the first snapshot "
                       f"({membership.index[0].date()})")
    return membership.iloc[idx]


def universe_over(membership: pd.Series, start, end) -> list[str]:
    """Every ticker that was a member at any point in [start, end].

    This is the download list. It is much larger than the current membership
    -- that difference IS the survivorship bias.
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    lo = max(membership.index.searchsorted(start, side="right") - 1, 0)
    hi = membership.index.searchsorted(end, side="right")
    out: set[str] = set()
    for s in membership.iloc[lo:hi]:
        out |= s
    return sorted(out)


def membership_mask(membership: pd.Series, dates, tickers) -> pd.DataFrame:
    """Boolean (dates x tickers) frame: was this ticker in the index then?

    Apply this to the panel BEFORE any cross-sectional ranking or clustering,
    so that non-members are excluded from the peer group as well as from
    selection.
    """
    dates = pd.DatetimeIndex(dates)
    tickers = list(tickers)
    rows = [
        pd.Series([t in members_on(membership, d) for t in tickers],
                  index=tickers, name=d)
        for d in dates
    ]
    return pd.DataFrame(rows)


def bias_report(membership: pd.Series, start, end) -> dict:
    """Quantify what a current-membership universe would have missed."""
    hist = set(universe_over(membership, start, end))
    current = set(membership.iloc[-1])
    missing = hist - current
    return {
        "members_at_some_point": len(hist),
        "still_members_today": len(hist & current),
        "left_the_index": len(missing),
        "pct_universe_missed": round(100 * len(missing) / len(hist), 1),
        "examples_missed": sorted(missing)[:15],
    }


if __name__ == "__main__":
    m = load_membership()
    print(f"snapshots: {len(m)}   {m.index[0].date()} -> {m.index[-1].date()}")
    rep = bias_report(m, "2011-06-30", "2026-06-30")
    for k, v in rep.items():
        print(f"  {k}: {v}")