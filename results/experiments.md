# Momentum experiments

Back test 2013-07-01 to 2026-06-29, split at 2021-07-01. SPY over the same days: Sharpe 0.88 (2013-21 0.93, 2021-26 0.81), CAGR 14.4%, max drawdown -33.7%.

| Variant | Sharpe 2013-21 | Sharpe 2021-26 | Sharpe | CAGR | Max DD | Names a month | RSI of cluster | Kept |
|---|---|---|---|---|---|---|---|---|
| legacy | 0.74 | 0.85 | 0.78 | 13.4% | -27.8% | 30.5 | 60.5 | False |
| fixed | 0.73 | 0.75 | 0.74 | 14.4% | -38.7% | 22.5 | 63.2 | False |
| K = 5 | 0.66 | 0.54 | 0.61 | 11.6% | -40.4% | 17.4 | 64.1 | False |
| K = 6 | 0.72 | 0.64 | 0.69 | 13.8% | -42.7% | 14.0 | 64.7 | False |
| K = 8 | 0.65 | 0.84 | 0.73 | 15.4% | -40.9% | 10.5 | 65.5 | False |
| shrunk_mu | 0.62 | 0.55 | 0.59 | 10.1% | -41.0% | 22.5 | 63.2 | False |
| min_variance | 0.62 | 0.47 | 0.56 | 9.4% | -41.0% | 22.5 | 63.2 | False |
| equal | 0.71 | 0.74 | 0.72 | 13.9% | -42.5% | 22.5 | 63.2 | False |
| extended | 0.9 | 0.87 | 0.89 | 17.4% | -29.4% | 24.6 | 62.6 | True |
| seeded | 0.96 | 0.74 | 0.86 | 19.3% | -30.3% | 18.5 | 60.6 | False |
| final | 0.9 | 0.87 | 0.89 | 17.4% | -29.4% | 24.6 | 62.6 | None |

Final changes: `{'features': 'extended'}`
