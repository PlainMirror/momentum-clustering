# Holdout test

## Step 1: choose on CRSP, 1999-2022 (halves split at 2011)

| design | Sharpe | CAGR_% | MaxDD_% | total_% | alpha_% | alpha_t | beta | Sharpe_1 | Sharpe_2 | names_per_month | rsi_of_cluster | qualifies |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fixed (reference) | 0.32 | 4.41 | -54.00 | 179.57 | 0.11 | 0.04 | 0.71 | 0.08 | 0.58 | 22.42 | 61.74 | False |
| M1 seeded on 12-1 momentum | 0.57 | 11.01 | -46.90 | 1104.63 | 5.65 | 1.89 | 0.88 | 0.53 | 0.61 | 18.94 | 56.05 | True |
| M2 + RSI the other way | 0.54 | 10.68 | -53.76 | 1021.84 | 5.85 | 1.70 | 0.85 | 0.51 | 0.58 | 18.74 | 47.54 | True |
| M3 + 52-week high, RSI the other way | 0.52 | 10.23 | -45.22 | 919.24 | 5.73 | 1.58 | 0.82 | 0.58 | 0.45 | 13.56 | 51.53 | False |

Chosen: **M1 seeded on 12-1 momentum**

## Step 2: the holdout, Yahoo 2023-01-01 to 2026-06-30, run once

| design | Sharpe | CAGR_% | MaxDD_% | total_% | alpha_% | alpha_t | beta |
|---|---|---|---|---|---|---|---|
| M1 seeded on 12-1 momentum | 1.06 | 30.41 | -27.67 | 152.30 | 0.79 | 0.08 | 1.40 |
| fixed (picked on 2013-26, reference) | 1.02 | 21.95 | -19.84 | 99.69 | 5.38 | 0.59 | 0.79 |
| extended (picked on 2013-26, reference) | 1.05 | 22.20 | -14.94 | 101.12 | 5.09 | 0.63 | 0.81 |
| SPY | 1.42 | 22.46 | -18.76 | 102.64 | nan | nan | nan |

