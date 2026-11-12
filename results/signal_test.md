# Signal tests

## final (three momentum features added)

20,999 stock-months, 156 months (2013-06-30 to 2026-05-31), 18.4% of them in the cluster.

### Fama-MacBeth 1. cluster alone (156 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.234 | 14.812 | 4.259 |
| top | 0.083 | 1.001 | 0.303 |
| return_1m | 0.063 | 0.752 | 0.494 |
| Mkt-RF | 0.401 | 4.816 | 3.263 |

### Fama-MacBeth 2. cluster + 12-1 momentum (156 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.260 | 15.114 | 4.399 |
| top | -0.143 | -1.719 | -0.469 |
| mom_12_1 | 0.211 | 2.526 | 1.189 |
| return_1m | 0.082 | 0.986 | 0.629 |
| Mkt-RF | 0.370 | 4.434 | 3.350 |

### Fama-MacBeth 3. cluster + all momentum features (156 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.288 | 15.460 | 4.384 |
| top | -0.205 | -2.458 | -0.715 |
| mom_12_1 | 0.346 | 4.154 | 1.665 |
| high_52w | -0.226 | -2.708 | -1.346 |
| mom_6m_risk_adj | 0.099 | 1.192 | 0.653 |
| rsi | -0.051 | -0.613 | -0.323 |
| return_1m | 0.184 | 2.210 | 0.981 |
| Mkt-RF | 0.277 | 3.324 | 2.921 |

### Fama-MacBeth 4. features alone, no cluster (156 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.268 | 15.211 | 4.364 |
| mom_12_1 | 0.337 | 4.048 | 1.619 |
| high_52w | -0.199 | -2.385 | -1.168 |
| mom_6m_risk_adj | 0.058 | 0.690 | 0.372 |
| rsi | -0.059 | -0.709 | -0.368 |
| return_1m | 0.160 | 1.915 | 0.871 |
| Mkt-RF | 0.264 | 3.174 | 2.791 |

### Factor-adjusted portfolios

| portfolio | model | months | alpha_annual_% | t | UMD_loading | UMD_t |
|---|---|---|---|---|---|---|
| cluster, equal weight, minus T-bill-free universe | raw mean | 156 | 2.524 | 0.984 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | Fama-French 5 | 156 | 4.984 | 2.071 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | FF5 + momentum (UMD) | 156 | 4.219 | 1.750 | 0.118 | 1.298 |
| cluster minus the rest (long-short) | raw mean | 156 | 2.937 | 0.967 | nan | nan |
| cluster minus the rest (long-short) | Fama-French 5 | 156 | 5.930 | 2.091 | nan | nan |
| cluster minus the rest (long-short) | FF5 + momentum (UMD) | 156 | 4.957 | 1.731 | 0.150 | 1.390 |

## fixed

20,999 stock-months, 156 months (2013-06-30 to 2026-05-31), 16.8% of them in the cluster.

### Fama-MacBeth 1. cluster alone (154 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.345 | 16.137 | 4.832 |
| top | -0.072 | -0.860 | -0.229 |
| return_1m | 0.092 | 1.106 | 0.702 |
| Mkt-RF | 0.408 | 4.900 | 3.310 |

### Fama-MacBeth 2. cluster + 12-1 momentum (154 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.363 | 16.358 | 4.958 |
| top | -0.283 | -3.401 | -0.841 |
| mom_12_1 | 0.215 | 2.577 | 1.222 |
| return_1m | 0.126 | 1.517 | 0.931 |
| Mkt-RF | 0.374 | 4.490 | 3.417 |

### Fama-MacBeth 3. cluster + all momentum features (154 months)

| variable | monthly_% | annual_% | t |
|---|---|---|---|
| const | 1.397 | 16.760 | 4.957 |
| top | -0.482 | -5.787 | -1.619 |
| mom_12_1 | 0.371 | 4.457 | 1.790 |
| high_52w | -0.272 | -3.265 | -1.685 |
| mom_6m_risk_adj | 0.105 | 1.261 | 0.686 |
| rsi | 0.005 | 0.057 | 0.030 |
| return_1m | 0.211 | 2.538 | 1.094 |
| Mkt-RF | 0.280 | 3.358 | 2.956 |

### Factor-adjusted portfolios

| portfolio | model | months | alpha_annual_% | t | UMD_loading | UMD_t |
|---|---|---|---|---|---|---|
| cluster, equal weight, minus T-bill-free universe | raw mean | 156 | 0.673 | 0.220 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | Fama-French 5 | 156 | 2.167 | 0.636 | nan | nan |
| cluster, equal weight, minus T-bill-free universe | FF5 + momentum (UMD) | 156 | 1.200 | 0.324 | 0.149 | 1.116 |
| cluster minus the rest (long-short) | raw mean | 156 | 0.758 | 0.217 | nan | nan |
| cluster minus the rest (long-short) | Fama-French 5 | 156 | 2.566 | 0.676 | nan | nan |
| cluster minus the rest (long-short) | FF5 + momentum (UMD) | 156 | 1.400 | 0.343 | 0.179 | 1.247 |

