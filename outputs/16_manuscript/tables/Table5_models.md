**Table5_models.** Mejor modelo por cultivo, variable y esquema de validación.

| crop     | target     | scheme     | model         |   r2_mean |   r2_std |   spearman_mean |   top20_mean |
|:---------|:-----------|:-----------|:--------------|----------:|---------:|----------------:|-------------:|
| chickpea | seedyield  | parcela    | TempCNN       |     0.849 |    0.023 |           0.921 |        0.444 |
| chickpea | seedyield  | genotipo   | TempCNN       |     0.826 |    0.033 |           0.914 |        0.424 |
| pea      | seedyield  | parcela    | TempCNN       |     0.717 |    0.028 |           0.817 |        0.368 |
| pea      | seedyield  | genotipo   | TempCNN       |     0.717 |    0.062 |           0.82  |        0.383 |
| chickpea | yield_z    | parcela    | XGBoost       |     0.511 |    0.089 |           0.718 |        0.502 |
| chickpea | yield_z    | genotipo   | XGBoost       |     0.495 |    0.048 |           0.715 |        0.44  |
| pea      | physmatur  | genotipo   | TempCNN       |     0.41  |    0.196 |           0.691 |        0.416 |
| pea      | physmatur  | parcela    | TempCNN       |     0.403 |    0.186 |           0.688 |        0.418 |
| chickpea | physmatur  | parcela    | XGBoost       |     0.36  |    0.121 |           0.605 |        0.337 |
| chickpea | physmatur  | genotipo   | Elastic Net   |     0.326 |    0.119 |           0.542 |        0.251 |
| pea      | fiftyflowr | parcela    | TempCNN       |     0.248 |    0.052 |           0.481 |        0.281 |
| chickpea | fiftyflowr | genotipo   | Random Forest |     0.242 |    0.17  |           0.505 |        0.421 |
| pea      | yield_z    | genotipo   | Random Forest |     0.232 |    0.028 |           0.469 |        0.391 |
| pea      | yield_z    | parcela    | Random Forest |     0.229 |    0.025 |           0.457 |        0.355 |
| chickpea | fiftyflowr | parcela    | Random Forest |     0.221 |    0.219 |           0.495 |        0.424 |
| pea      | fiftyflowr | genotipo   | TempCNN       |     0.194 |    0.114 |           0.484 |        0.299 |
| pea      | yield_z    | año futuro | Random Forest |     0.122 |  nan     |           0.384 |        0.365 |
| chickpea | yield_z    | año futuro | LASSO         |    -0.037 |  nan     |           0.557 |        0.238 |
| pea      | yield_z    | ambiente   | Random Forest |    -0.045 |    0.126 |           0.285 |        0.311 |
| chickpea | physmatur  | año futuro | TempCNN       |    -0.048 |  nan     |          -0.188 |        0.143 |
| chickpea | fiftyflowr | año futuro | TempCNN       |    -0.097 |  nan     |          -0.163 |        0.214 |
| pea      | seedyield  | año futuro | TempCNN       |    -0.132 |  nan     |          -0.157 |        0.253 |
| chickpea | fiftyflowr | ambiente   | LASSO         |    -0.251 |    0.022 |           0.159 |        0.291 |
| chickpea | seedyield  | año futuro | PLSR          |    -0.279 |  nan     |           0.494 |        0.286 |
| pea      | fiftyflowr | año futuro | TempCNN       |    -0.284 |  nan     |           0.078 |        0.125 |
| pea      | fiftyflowr | ambiente   | TempCNN       |    -0.716 |    0.864 |           0.054 |        0.235 |
| chickpea | yield_z    | ambiente   | Random Forest |    -1.062 |    2.045 |           0.376 |        0.34  |
| chickpea | physmatur  | ambiente   | XGBoost       |    -1.149 |    1.498 |           0.11  |        0.227 |
| pea      | physmatur  | ambiente   | PLSR          |    -1.307 |    0.699 |           0.169 |        0.251 |
| pea      | physmatur  | año futuro | TempCNN       |    -1.491 |  nan     |           0.194 |        0.293 |
| pea      | seedyield  | ambiente   | TempCNN       |    -4.188 |    6.512 |           0.014 |        0.204 |
| chickpea | seedyield  | ambiente   | TempCNN       |    -6.685 |   10.856 |           0.353 |        0.332 |
