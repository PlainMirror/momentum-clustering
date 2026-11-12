# Signal tests (crsp)

## final (three momentum features added)

36,230 stock-months, 286 months (1999-02-28 to 2022-11-30), 18.6% of them in the cluster.

### Fama-MacBeth 1. cluster alone (286 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.725 | 8.696 | 2.776 |
| top | -0.048 | -0.579 | -0.215 |
| return_1m | -0.091 | -1.093 | -0.973 |
| Mkt-RF | 0.008 | 0.093 | 0.100 |

### Fama-MacBeth 2. cluster + 12-1 momentum (286 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.767 | 9.200 | 3.008 |
| top | -0.324 | -3.883 | -1.940 |
| mom_12_1 | 0.202 | 2.426 | 1.635 |
| return_1m | -0.043 | -0.518 | -0.504 |
| Mkt-RF | -0.021 | -0.249 | -0.309 |

### Fama-MacBeth 3. cluster + all momentum features (286 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.690 | 8.279 | 2.651 |
| top | 0.030 | 0.360 | 0.185 |
| mom_12_1 | 0.271 | 3.249 | 2.120 |
| high_52w | 0.038 | 0.453 | 0.255 |
| mom_6m_risk_adj | -0.087 | -1.049 | -0.843 |
| rsi | -0.288 | -3.458 | -2.649 |
| return_1m | 0.132 | 1.588 | 1.268 |
| Mkt-RF | -0.035 | -0.418 | -0.582 |

### Fama-MacBeth 4. features alone, no cluster (286 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.683 | 8.197 | 2.615 |
| mom_12_1 | 0.278 | 3.334 | 2.209 |
| high_52w | 0.028 | 0.330 | 0.187 |
| mom_6m_risk_adj | -0.067 | -0.805 | -0.656 |
| rsi | -0.329 | -3.950 | -2.980 |
| return_1m | 0.165 | 1.982 | 1.607 |
| Mkt-RF | -0.028 | -0.332 | -0.474 |

### Factor-adjusted portfolios

| portfolio | model | months | alpha_annual_% | t | UMD_loading | UMD_t |
|---|---|---|---|---|---|---|
| cluster, equal weight, minus T-bill-free universe | raw mean | 286 | -0.899 | -0.380 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | Fama-French 5 | 286 | -1.246 | -0.535 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | FF5 + momentum (UMD) | 286 | -2.031 | -0.991 | 0.191 | 2.967 |
| cluster minus the rest (long-short) | raw mean | 286 | -1.607 | -0.583 | nan | nan |
| cluster minus the rest (long-short) | Fama-French 5 | 286 | -2.074 | -0.760 | nan | nan |
| cluster minus the rest (long-short) | FF5 + momentum (UMD) | 286 | -3.017 | -1.245 | 0.230 | 3.006 |

## fixed

36,230 stock-months, 286 months (1999-02-28 to 2022-11-30), 17.6% of them in the cluster.

### Fama-MacBeth 1. cluster alone (285 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.753 | 9.039 | 2.884 |
| top | -0.235 | -2.816 | -0.982 |
| return_1m | -0.037 | -0.445 | -0.412 |
| Mkt-RF | 0.008 | 0.100 | 0.106 |

### Fama-MacBeth 2. cluster + 12-1 momentum (285 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.781 | 9.376 | 3.047 |
| top | -0.445 | -5.341 | -2.555 |
| mom_12_1 | 0.170 | 2.036 | 1.412 |
| return_1m | -0.000 | -0.002 | -0.002 |
| Mkt-RF | -0.009 | -0.106 | -0.130 |

### Fama-MacBeth 3. cluster + all momentum features (285 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 0.721 | 8.650 | 2.756 |
| top | -0.102 | -1.220 | -0.580 |
| mom_12_1 | 0.252 | 3.026 | 2.010 |
| high_52w | 0.032 | 0.379 | 0.214 |
| mom_6m_risk_adj | -0.054 | -0.648 | -0.527 |
| rsi | -0.278 | -3.338 | -2.482 |
| return_1m | 0.152 | 1.819 | 1.453 |
| Mkt-RF | -0.027 | -0.319 | -0.440 |

### Factor-adjusted portfolios

| portfolio | model | months | alpha_annual_% | t | UMD_loading | UMD_t |
|---|---|---|---|---|---|---|
| cluster, equal weight, minus T-bill-free universe | raw mean | 286 | -2.937 | -1.153 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | Fama-French 5 | 286 | -2.938 | -1.154 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | FF5 + momentum (UMD) | 286 | -3.529 | -1.524 | 0.144 | 2.010 |
| cluster minus the rest (long-short) | raw mean | 286 | -3.966 | -1.344 | nan | nan |
| cluster minus the rest (long-short) | Fama-French 5 | 286 | -3.985 | -1.351 | nan | nan |
| cluster minus the rest (long-short) | FF5 + momentum (UMD) | 286 | -4.700 | -1.746 | 0.174 | 2.112 |

