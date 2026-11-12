# Momentum Clustering on Point-in-Time S&P 500 Members

I wanted to see whether K-means can find a group of stocks with momentum each month, and whether holding that group, weighted by a maximum-Sharpe optimiser, beats the S&P 500. My first version beat SPY easily. That turned out to be survivorship bias, because I had used today's index list for the whole back test. After rebuilding the universe from point-in-time membership it only matched SPY. This version fixes three more bugs I found later, and tests four ideas for improving it, each against a rule I wrote down before running anything.

Research code. It places no orders and is not financial advice.

## How it works

Every month, among the 150 most liquid stocks that were in the S&P 500 at the time (membership from `sp500_pit.py`, so firms that later left the index are included):

1. Features per stock: Garman-Klass volatility, 20-day RSI, where the price sits in its Bollinger band, ATR and MACD (both z-scored against their own past), past returns over 1, 2, 3, 6, 9 and 12 months, and rolling 24-month Fama-French five-factor betas, lagged a month so they never use the month being traded.
2. Every feature is z-scored across stocks on that date, and K-means groups them into 4 clusters. The starting centroids are seeded at fixed RSI levels (-1.5 to +1.5), so the top cluster means "high RSI" every month instead of whatever the random start happens to give.
3. The top cluster's stocks with a positive 12-month return are held for the next month, weighted by maximum Sharpe on a Ledoit-Wolf covariance, capped at 10% a name, with 10 basis points of cost per unit of turnover.

## Bugs fixed (2026-11-11)

| Bug | What it did | Fix |
|---|---|---|
| Garman-Klass volatility used the dividend-adjusted close with the unadjusted open | On older dates for dividend payers, the close-to-open term measured the dividend adjustment, not the day's move | All four prices from the same unadjusted series (the estimator only uses ratios within one day) |
| Bollinger band levels were fed to K-means | They are log price levels, so across stocks they mostly sort by share price | Replaced by where the price sits inside its band (%B) |
| Only RSI was standardised before clustering | Features on bigger scales dominated the distances K-means uses | Every feature z-scored across stocks on each date |
| Past returns were clipped at each stock's own full-history quantiles | The clip on a 2014 return used prices from 2026 | Clipped across stocks on each date instead |

Before these fixes the top cluster's average RSI was 60.5 against 52 for everyone. After them it is 63.2, so the cluster now picks high-RSI stocks more cleanly. The Sharpe ratio went slightly down, though, from 0.78 to 0.74, so part of the old result came from the bugs.

## Which ideas helped? (`experiments.py`)

Each idea changes one thing from the fixed version, over July 2013 to June 2026. The rule, written before the first run: a change is kept only if its Sharpe beats the fixed version's in both halves, July 2013 to June 2021 and July 2021 to June 2026. A change that only helps in one half is usually fitted to that half.

| Variant | Sharpe 2013-21 | Sharpe 2021-26 | Sharpe | CAGR | Max drawdown | Stocks a month |
|---|---|---|---|---|---|---|
| before the fixes | 0.74 | 0.85 | 0.78 | 13.4% | -27.8% | 30.5 |
| **fixed (the baseline)** | 0.73 | 0.75 | 0.74 | 14.4% | -38.7% | 22.5 |
| 5 clusters | 0.66 | 0.54 | 0.61 | 11.6% | -40.4% | 17.4 |
| 6 clusters | 0.72 | 0.64 | 0.69 | 13.8% | -42.7% | 14.0 |
| 8 clusters | 0.65 | 0.84 | 0.73 | 15.4% | -40.9% | 10.5 |
| expected returns shrunk (James-Stein) | 0.62 | 0.55 | 0.59 | 10.1% | -41.0% | 22.5 |
| no expected returns (minimum variance) | 0.62 | 0.47 | 0.56 | 9.4% | -41.0% | 22.5 |
| equal weights | 0.71 | 0.74 | 0.72 | 13.9% | -42.5% | 22.5 |
| **three momentum features added** | **0.90** | **0.87** | **0.89** | **17.4%** | **-29.4%** | 24.6 |
| the same three, also seeded like RSI | 0.96 | 0.74 | 0.86 | 19.3% | -30.3% | 18.5 |
| SPY | 0.93 | 0.81 | 0.88 | 14.4% | -33.7% | |

Only one change passed: adding three momentum features to the clustering. They are all published predictors, chosen before the run:

- 12-1 month momentum: the return from 12 months ago to 1 month ago, skipping the most recent month because it tends to reverse (Jegadeesh and Titman, 1993);
- distance to the 52-week high: price divided by its 12-month high (George and Hwang, 2004);
- volatility-scaled momentum: the 6-month return divided by 6-month volatility.

A few things stand out:

- **More clusters didn't help.** Each extra cluster splits the top group, so 8 clusters hold about 10 stocks a month instead of 22. That is noisier, not sharper, and 8 clusters did better only in the second half.
- **Reducing the noise in expected returns made it worse, which surprised me.** Both shrinkage and minimum variance lowered Sharpe in both halves. Looking at it again, it makes sense: the "expected return" fed to the optimiser is each stock's past-year average, which is itself a momentum signal. Shrinking it toward the group average takes out the very tilt the strategy is built on, and minimum variance drifts into the calm, low-momentum names of the cluster.
- **Seeding the three new features as well as RSI** was the best version in the first half (0.96) and by CAGR (19.3%), but it missed the fixed version's second half by 0.007 (0.742 against 0.749). Under the rule it isn't kept, which is the point of having the rule.

## The final version against SPY

With the three features added (July 2013 to June 2026, daily returns):

| | Strategy | SPY |
|---|---|---|
| total return | 701% | 476% |
| CAGR | 17.4% | 14.4% |
| Sharpe | 0.89 | 0.88 |
| Sortino | 1.27 | |
| max drawdown | -29.4% | -33.7% |
| beta to SPY | 0.87 | 1 |
| alpha a year | 5.1% (t = 1.40) | |

So it makes about 3 points a year more than SPY with a smaller drawdown, at the same Sharpe ratio. However, the alpha has a t-statistic of 1.40, which is not significant, and it is the one change kept out of nine tried. Taking this into account, I read it as momentum features genuinely helping the clustering, but not as an established edge over the index.

## Limitations

1. **Prices for the companies that left.** Yahoo served 622 of the 822 stocks that were in the index at some point. Most of the 200 missing ones were delisted, acquired or went bankrupt, and those tend to be the poor performers, so the results are still optimistic. A few live names (BK, EA, EQR) also returned nothing on the day this ran, which looks like a Yahoo problem rather than delisting. CRSP through WRDS would fix both.
2. **Delisting returns.** A position whose prices stop mid-month is treated as cash at its last price, which understates a bankruptcy.
3. **Ticker reuse.** Membership is matched on ticker, so a recycled symbol can pick up the wrong company's history.
4. **One split.** Two halves is the least a robustness check can be. With nine variants tested, one passing by chance is plausible.
5. **Costs** are a flat 10 basis points of turnover, with no market impact.

## Running it

```bash
pip install -r requirements.txt
python momentum.py          # downloads once (about 3 minutes), caches to cache/, runs the fixed version
python experiments.py       # all variants in parallel (about 2 minutes on 6 cores)
python retry_download.py    # retries tickers Yahoo returned nothing for
```

| File | What it is |
|---|---|
| `momentum.py` | data, features, clustering, weighting, back test and evaluation |
| `experiments.py` | the pre-registered variants and the keep rule |
| `sp500_pit.py` | point-in-time S&P 500 membership (also its own repo, `sp500-point-in-time`) |
| `results/experiments.md`, `.csv` | every variant's numbers |

Tested with Python 3.13.
