# Momentum Clustering

A monthly K-means momentum strategy on large US stocks: cluster the universe on technical, factor and momentum features, hold the momentum cluster, and weight it with a maximum-Sharpe optimiser.

Research code. It places no orders and is not financial advice.

## The model

- **Universe:** the 500 largest US stocks each month from CRSP, 1997 to 2022, which keeps delisted firms (no survivorship bias). The strategy trades the largest 150.
- **Features:** RSI, MACD, Bollinger %B, volatility, ATR, past returns, rolling Fama-French five-factor betas, and three momentum factors:
  - 12-1 month momentum (the return from 12 months ago to 1 month ago);
  - distance to the 52-week high;
  - volatility-scaled 6-month momentum.
- **Clustering:** every feature is z-scored across stocks each month, and K-means groups them into 4 clusters. The starting centroids are seeded on 12-1 month momentum, so the top cluster means "strong long-run trend" every month.
- **Portfolio:** the top cluster's stocks with a positive 12-month return, weighted by maximum Sharpe on a Ledoit-Wolf covariance (10% cap per name), rebalanced monthly with 10 basis points of cost per unit of turnover.

## Results

**1999 to 2022 (CRSP):**

| | Strategy | SPY |
|---|---|---|
| CAGR | 11.0% | 6.8% |
| total return | 1,105% | 377% |
| Sharpe | 0.57 | 0.43 |
| max drawdown | -46.9% | -55.2% |
| alpha a year | 5.7% (t = 1.89) | |
| beta | 0.88 | |

**Holdout, January 2023 to June 2026 (Yahoo, point-in-time S&P 500), run once:**

| | Strategy | SPY |
|---|---|---|
| total return | 152% | 103% |
| CAGR | 30.4% | 22.5% |
| Sharpe | 1.06 | 1.42 |
| alpha a year | 0.8% (t = 0.08) | |
| beta | 1.40 | |

(Sharpe is the mean daily return over its standard deviation for both, with no risk-free rate subtracted.)

The holdout's extra return came from a higher beta, not alpha: the strongest 12-month trends in 2023 to 2026 were high-beta technology stocks.

## How it was tested

- **One change at a time.** Each design change was kept only if it raised Sharpe in both halves of the sample (1999 to 2010 and 2011 to 2022), with the rule written down before anything ran (`experiments.py`).
- **Across stocks.** Fama-MacBeth regressions over 286 months show 12-1 momentum predicts higher next-month returns (t = 2.2) and 20-day RSI lower ones (t = -3.0), which is why the centroids are seeded on momentum (`signal_test.py`).
- **Once on unseen data.** The final design was chosen on CRSP and then run once on 2023 to 2026, data the choice never saw (`holdout.py`).

Full tables are in `results/`.

## Limitations

- Alpha is not significant at the usual 5% level (t = 1.89), and the holdout is only 3.5 years.
- The CRSP files have no delisting returns, so a bankruptcy drops out at its last price rather than near -100%.
- CRSP here has daily returns but no high, low or volume, so volatility and ATR use close-to-close versions and the universe is ranked by size.
- Yahoo, used for 2011 onward and the holdout, is missing most delisted stocks (it served 622 of 822 past S&P 500 members).

## Running it

```bash
pip install -r requirements.txt
python momentum.py             # Yahoo data, 2011-2026: downloads once and caches to cache/
python experiments.py          # design changes, both halves
python signal_test.py          # Fama-MacBeth and factor-adjusted tests

# CRSP, 1997-2022 (licensed data, not included; set CRSP_DIR)
python crsp_data.py
MOM_DATA=crsp python experiments.py
MOM_DATA=crsp python signal_test.py
python holdout.py              # choose on CRSP, test once on 2023-2026
```

| File | What it is |
|---|---|
| `momentum.py` | data, features, clustering, weighting, back test and evaluation |
| `crsp_data.py` | the same panel built from CRSP |
| `experiments.py`, `signal_test.py`, `holdout.py` | the tests above |
| `sp500_pit.py` | point-in-time S&P 500 membership |
| `results/` | every table |

Tested with Python 3.13.
