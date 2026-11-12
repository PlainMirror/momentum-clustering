# Momentum experiments (crsp)

Back test 1999-03-01 to 2022-12-30, split at 2011-01-01. SPY over the same days: Sharpe 0.43 (1999-2010 0.20, 2011-22 0.72), CAGR 6.8%, max drawdown -55.2%.

| Variant | Sharpe 1999-2010 | Sharpe 2011-22 | Sharpe | CAGR | Max DD | Names a month | RSI of cluster | Kept |
|---|---|---|---|---|---|---|---|---|
| fixed | 0.08 | 0.58 | 0.32 | 4.4% | -54.0% | 22.4 | 61.7 | False |
| K = 5 | 0.09 | 0.59 | 0.33 | 4.6% | -54.5% | 16.9 | 62.4 | True |
| K = 6 | 0.25 | 0.64 | 0.44 | 7.0% | -54.3% | 13.3 | 63.2 | True |
| K = 8 | 0.18 | 0.55 | 0.36 | 5.4% | -52.9% | 10.6 | 64.0 | False |
| shrunk_mu | -0.05 | 0.62 | 0.28 | 3.3% | -56.7% | 22.4 | 61.7 | False |
| min_variance | -0.05 | 0.63 | 0.28 | 3.4% | -56.8% | 22.4 | 61.7 | False |
| equal | -0.04 | 0.63 | 0.28 | 3.6% | -61.7% | 22.4 | 61.7 | False |
| extended | 0.1 | 0.72 | 0.4 | 5.9% | -52.6% | 23.7 | 61.4 | True |
| seeded | 0.32 | 0.69 | 0.49 | 8.5% | -49.3% | 18.6 | 60.3 | True |
| final | 0.33 | 0.48 | 0.4 | 7.2% | -60.9% | 8.4 | 60.7 | None |

Final changes: `{'n_clusters': 6, 'features': 'extended', 'seed_features': ('rsi', 'mom_12_1', 'high_52w', 'mom_6m_risk_adj')}`
