# Resumen de resultados (generado automáticamente)

**Table1_trials.** Ensayos, parcelas, rendimiento medio (kg/ha), CV (%) y repetibilidad del rendimiento.

|   year | site      | trial   | crop_by_code   |   n_plots |   n_entries |   yield_mean |   yield_cv |   h2_yield |
|-------:|:----------|:--------|:---------------|----------:|------------:|-------------:|-----------:|-----------:|
|   2017 | Fairfield | 1701    | pea            |       120 |          40 |      1981.77 |      23.25 |       0.17 |
|   2017 | Fairfield | 1701B   | pea            |        57 |          19 |      2683.71 |      23.11 |       0.23 |
|   2017 | Fairfield | 1702    | pea            |        63 |          21 |      2753.94 |      20.37 |       0.45 |
|   2017 | Pullman   | 1701    | pea            |       120 |          40 |      1288.88 |      18.63 |       0.74 |
|   2017 | Pullman   | 1701B   | pea            |        57 |          19 |      1383.5  |      25.93 |       0.86 |
|   2017 | Pullman   | 1702    | pea            |        63 |          21 |      1166.9  |      25.87 |       0.66 |
|   2017 | Pullman   | 1703    | pea            |        36 |          12 |      1365.03 |      13.69 |       0.91 |
|   2017 | Pullman   | 1704    | pea            |        18 |           6 |      1514.46 |      14.07 |       0.73 |
|   2017 | Pullman   | 1781    | chickpea       |        72 |          24 |       995.19 |      28.78 |       0.75 |
|   2017 | Pullman   | 1781G   | chickpea       |        24 |           8 |       675.48 |      46.84 |       0.94 |
|   2018 | Fairfield | 1801    | pea            |        96 |          32 |      2238.74 |      13.29 |       0.39 |
|   2018 | Fairfield | 1802    | pea            |        69 |          23 |      2341.89 |      13.4  |       0.74 |
|   2018 | Fairfield | 1881    | chickpea       |        63 |          21 |       933.48 |      20.69 |       0.59 |
|   2018 | Genesee   | 1801    | pea            |        96 |          32 |      3599.54 |      12.77 |       0.57 |
|   2018 | Genesee   | 1881    | chickpea       |        63 |          21 |      3034.61 |      19.75 |       0.58 |
|   2018 | Pullman   | 1801    | pea            |        96 |          32 |      2740.19 |       8.98 |       0.69 |
|   2018 | Pullman   | 1802    | pea            |        69 |          23 |      2730.13 |      12.57 |       0.93 |
|   2018 | Pullman   | 1803    | pea            |        90 |          30 |      2472.89 |      12.15 |       0.83 |
|   2018 | Pullman   | 1804    | pea            |        60 |          20 |      2531.19 |      12.85 |       0.82 |
|   2018 | Pullman   | 1881    | chickpea       |        63 |          21 |      2162.52 |       9.82 |       0.81 |
|   2018 | Pullman   | 1883    | chickpea       |        66 |          33 |      2042.76 |      10.22 |       0.82 |
|   2019 | Fairfield | 1901    | pea            |        87 |          29 |      2543.69 |      18.81 |       0.67 |
|   2019 | Fairfield | 1902    | pea            |        69 |          23 |      2615.05 |      13.84 |       0.55 |
|   2019 | Fairfield | 1981    | chickpea       |        72 |          24 |      1566.81 |      29.04 |       0.68 |
|   2019 | Genesee   | 1901    | pea            |        87 |          29 |      3118.37 |      13.69 |       0.76 |
|   2019 | Genesee   | 1901B   | pea            |        48 |          16 |      3283.32 |      11.99 |       0.83 |
|   2019 | Genesee   | 1981    | chickpea       |        72 |          24 |      2484.26 |      15.87 |       0.79 |
|   2019 | Pullman   | 1901    | pea            |        87 |          29 |      1662.58 |      25.89 |       0.71 |
|   2019 | Pullman   | 1901B   | pea            |        48 |          16 |      2117.8  |      24.65 |       0.78 |
|   2019 | Pullman   | 1902    | pea            |        69 |          23 |      2134.8  |      21.1  |       0.58 |
|   2019 | Pullman   | 1903    | pea            |       102 |          34 |      2130.16 |      17.04 |       0.19 |
|   2019 | Pullman   | 1904    | pea            |        69 |          23 |      2024.67 |      20.97 |       0.56 |
|   2019 | Pullman   | 1981    | chickpea       |        72 |          24 |      2098.84 |      16.82 |       0.84 |
|   2019 | Pullman   | 1983    | chickpea       |        72 |          24 |      2009.38 |      14.72 |       0.52 |

**Table2_calibration.** R² agrupado de la calibración UAV→Sentinel-2 (modelo adoptado).

|   year |   blue |   green |   nir |   red |   red edge |
|-------:|-------:|--------:|------:|------:|-----------:|
|   2017 |  0.589 |  -0.068 | 0.615 | 0.74  |      0.762 |
|   2018 |  0.806 |   0.755 | 0.8   | 0.898 |      0.882 |
|   2019 |  0.864 |   0.702 | 0.949 | 0.951 |      0.784 |

**Table3_replication.** R² de prueba de LASSO: publicado vs réplica.

| market_class    | dataset        | level    |   r2_zhang | variant   |      r2 |
|:----------------|:---------------|:---------|-----------:|:----------|--------:|
| kabuli_chickpea | 2017_Pullman   | parcela  |       0.32 | original  | nan     |
| kabuli_chickpea | 2017_Pullman   | parcela  |       0.32 | anidada   |  -0.052 |
| kabuli_chickpea | 2018_Pullman   | parcela  |       0.53 | original  |   0.158 |
| kabuli_chickpea | 2018_Pullman   | parcela  |       0.53 | anidada   |   0.187 |
| kabuli_chickpea | 2018_Genesee   | parcela  |       0.33 | original  |  -0.1   |
| kabuli_chickpea | 2018_Genesee   | parcela  |       0.33 | anidada   |   0.018 |
| kabuli_chickpea | 2019_Pullman   | parcela  |       0.57 | original  |   0.505 |
| kabuli_chickpea | 2019_Pullman   | parcela  |       0.57 | anidada   |   0.34  |
| kabuli_chickpea | 2019_Genesee   | parcela  |       0.51 | original  |   0.695 |
| kabuli_chickpea | 2019_Genesee   | parcela  |       0.51 | anidada   |   0.496 |
| kabuli_chickpea | 2019_Fairfield | parcela  |       0.7  | original  |  -0.047 |
| kabuli_chickpea | 2019_Fairfield | parcela  |       0.7  | anidada   |   0.272 |
| kabuli_chickpea | 2018_combinado | parcela  |       0.89 | original  |   0.279 |
| kabuli_chickpea | 2018_combinado | parcela  |       0.89 | anidada   |   0.227 |
| kabuli_chickpea | 2019_combinado | parcela  |       0.82 | original  |   0.172 |
| kabuli_chickpea | 2019_combinado | parcela  |       0.82 | anidada   |   0.144 |
| kabuli_chickpea | 2018_combinado | cultivar |       0.91 | original  |   0.363 |
| kabuli_chickpea | 2018_combinado | cultivar |       0.91 | anidada   |   0.322 |
| kabuli_chickpea | 2019_combinado | cultivar |       0.76 | original  |   0.429 |
| kabuli_chickpea | 2019_combinado | cultivar |       0.76 | anidada   |   0.325 |

**Table4_heritability.** Heredabilidad (H²) por clase comercial y rasgo.

| market_class        | kind          | trait                         |   median |   min |   max |   count |
|:--------------------|:--------------|:------------------------------|---------:|------:|------:|--------:|
| green_chickpea      | UAV por vuelo | MCARI_mean                    |     0    |  0    |  0    |       1 |
| green_chickpea      | UAV por vuelo | NDVI_mean                     |     0    |  0    |  0    |       1 |
| green_chickpea      | campo/curva   | seedyield                     |     0.92 |  0.92 |  0.92 |       1 |
| green_chickpea      | campo/curva   | vinelength                    |     0.75 |  0.75 |  0.75 |       1 |
| green_pea           | UAV por vuelo | CIrededge_mean                |     0.55 |  0.07 |  0.88 |       6 |
| green_pea           | UAV por vuelo | GNDVI_mean                    |     0.79 |  0.34 |  0.9  |       8 |
| green_pea           | UAV por vuelo | MCARI_mean                    |     0.65 |  0    |  0.86 |      10 |
| green_pea           | UAV por vuelo | NDRE_mean                     |     0.72 |  0    |  0.9  |       6 |
| green_pea           | UAV por vuelo | NDVI_mean                     |     0.89 |  0.68 |  0.93 |       5 |
| green_pea           | UAV por vuelo | NDVI_sum                      |     0.6  |  0    |  0.87 |      10 |
| green_pea           | UAV por vuelo | TVI_mean                      |     0.7  |  0.1  |  0.86 |      11 |
| green_pea           | UAV por vuelo | canopy_area_m2                |     0.44 |  0    |  0.82 |      10 |
| green_pea           | UAV por vuelo | canopy_cover                  |     0.76 |  0.07 |  0.82 |       7 |
| green_pea           | campo/curva   | NDVI_plotmean:auc             |     0.53 |  0.37 |  0.7  |       2 |
| green_pea           | campo/curva   | NDVI_plotmean:max_rate        |     0    |  0    |  0    |       1 |
| green_pea           | campo/curva   | NDVI_plotmean:senescence_rate |     0.38 |  0    |  0.76 |       2 |
| green_pea           | campo/curva   | NDVI_plotmean:ymax            |     0.43 |  0.43 |  0.43 |       1 |
| green_pea           | campo/curva   | canopy_cover:max_rate         |     0.44 |  0.44 |  0.44 |       1 |
| green_pea           | campo/curva   | canopy_cover:senescence_rate  |     0.72 |  0    |  0.74 |       3 |
| green_pea           | campo/curva   | canopy_cover:x0               |     0    |  0    |  0    |       3 |
| green_pea           | campo/curva   | canopy_cover:ymax             |     0.28 |  0.28 |  0.28 |       1 |
| green_pea           | campo/curva   | canopyht                      |     0.89 |  0.87 |  0.91 |       3 |
| green_pea           | campo/curva   | fiftyflowr                    |     0.97 |  0.94 |  0.99 |       5 |
| green_pea           | campo/curva   | physmatur                     |     0.88 |  0.88 |  0.88 |       1 |
| green_pea           | campo/curva   | seedyield                     |     0.81 |  0.77 |  0.83 |       5 |
| green_pea           | campo/curva   | vinelength                    |     0.88 |  0.87 |  0.9  |       3 |
| kabuli_chickpea     | UAV por vuelo | CIrededge_mean                |     0.39 |  0.29 |  0.9  |       4 |
| kabuli_chickpea     | UAV por vuelo | GNDVI_mean                    |     0.86 |  0    |  0.97 |      14 |
| kabuli_chickpea     | UAV por vuelo | MCARI_mean                    |     0.8  |  0.35 |  0.91 |       7 |
| kabuli_chickpea     | UAV por vuelo | NDRE_mean                     |     0.77 |  0    |  0.9  |       3 |
| kabuli_chickpea     | UAV por vuelo | NDVI_mean                     |     0.84 |  0.69 |  0.96 |      12 |
| kabuli_chickpea     | UAV por vuelo | NDVI_sum                      |     0.84 |  0    |  0.95 |      13 |
| kabuli_chickpea     | UAV por vuelo | TVI_mean                      |     0.87 |  0.68 |  0.92 |       9 |
| kabuli_chickpea     | UAV por vuelo | canopy_area_m2                |     0.84 |  0    |  0.94 |      10 |
| kabuli_chickpea     | UAV por vuelo | canopy_cover                  |     0.83 |  0    |  0.94 |      12 |
| kabuli_chickpea     | campo/curva   | NDVI_plotmean:auc             |     0.73 |  0.49 |  0.94 |       3 |
| kabuli_chickpea     | campo/curva   | NDVI_plotmean:senescence_rate |     0.63 |  0.63 |  0.63 |       1 |
| kabuli_chickpea     | campo/curva   | NDVI_plotmean:x0              |     0.01 |  0.01 |  0.01 |       1 |
| kabuli_chickpea     | campo/curva   | NDVI_plotmean:ymax            |     0.95 |  0.95 |  0.95 |       1 |
| kabuli_chickpea     | campo/curva   | canopy_cover:auc              |     0.93 |  0.93 |  0.93 |       1 |
| kabuli_chickpea     | campo/curva   | canopy_cover:max_rate         |     0.89 |  0.89 |  0.89 |       1 |
| kabuli_chickpea     | campo/curva   | canopy_cover:senescence_rate  |     0.36 |  0.36 |  0.36 |       1 |
| kabuli_chickpea     | campo/curva   | canopy_cover:x0               |     0.64 |  0.64 |  0.64 |       1 |
| kabuli_chickpea     | campo/curva   | canopy_cover:ymax             |     0.46 |  0    |  0.92 |       2 |
| kabuli_chickpea     | campo/curva   | canopyht                      |     0.89 |  0.88 |  0.89 |       3 |
| kabuli_chickpea     | campo/curva   | fiftyflowr                    |     0.87 |  0.85 |  0.89 |       2 |
| kabuli_chickpea     | campo/curva   | physmatur                     |     0.91 |  0.84 |  0.94 |       4 |
| kabuli_chickpea     | campo/curva   | seedyield                     |     0.8  |  0.77 |  0.87 |       4 |
| kabuli_chickpea     | campo/curva   | vinelength                    |     0.84 |  0.79 |  0.86 |       3 |
| nz_green_yellow_pea | UAV por vuelo | CIrededge_mean                |     0.04 |  0    |  0.77 |       3 |
| nz_green_yellow_pea | UAV por vuelo | GNDVI_mean                    |     0.78 |  0.07 |  0.84 |       3 |
| nz_green_yellow_pea | UAV por vuelo | MCARI_mean                    |     0.79 |  0    |  0.93 |       3 |
| nz_green_yellow_pea | UAV por vuelo | NDRE_mean                     |     0.62 |  0.46 |  0.77 |       2 |
| nz_green_yellow_pea | UAV por vuelo | NDVI_mean                     |     0.76 |  0.01 |  0.84 |       3 |
| nz_green_yellow_pea | UAV por vuelo | NDVI_sum                      |     0.73 |  0.48 |  0.79 |       4 |
| nz_green_yellow_pea | UAV por vuelo | TVI_mean                      |     0.74 |  0.74 |  0.74 |       1 |
| nz_green_yellow_pea | UAV por vuelo | canopy_area_m2                |     0.75 |  0.61 |  0.78 |       3 |
| nz_green_yellow_pea | UAV por vuelo | canopy_cover                  |     0.44 |  0    |  0.78 |       5 |
| nz_green_yellow_pea | campo/curva   | canopy_cover:ymax             |     0.41 |  0.41 |  0.41 |       1 |
| nz_green_yellow_pea | campo/curva   | canopyht                      |     0.79 |  0.79 |  0.89 |       3 |
| nz_green_yellow_pea | campo/curva   | fiftyflowr                    |     0.99 |  0.99 |  0.99 |       1 |
| nz_green_yellow_pea | campo/curva   | physmatur                     |     0.83 |  0.83 |  0.83 |       1 |
| nz_green_yellow_pea | campo/curva   | seedyield                     |     0.87 |  0.77 |  0.89 |       3 |
| nz_green_yellow_pea | campo/curva   | vinelength                    |     0.8  |  0.8  |  0.88 |       3 |
| yellow_pea          | UAV por vuelo | CIrededge_mean                |     0.86 |  0.03 |  0.95 |       3 |
| yellow_pea          | UAV por vuelo | GNDVI_mean                    |     0.78 |  0    |  0.83 |       8 |
| yellow_pea          | UAV por vuelo | MCARI_mean                    |     0    |  0    |  0.85 |       5 |
| yellow_pea          | UAV por vuelo | NDRE_mean                     |     0.52 |  0.02 |  0.95 |       5 |
| yellow_pea          | UAV por vuelo | NDVI_mean                     |     0.76 |  0    |  0.94 |       8 |
| yellow_pea          | UAV por vuelo | NDVI_sum                      |     0.84 |  0.47 |  0.93 |       9 |
| yellow_pea          | UAV por vuelo | TVI_mean                      |     0.79 |  0    |  0.91 |       7 |
| yellow_pea          | UAV por vuelo | canopy_area_m2                |     0.8  |  0    |  0.92 |      10 |
| yellow_pea          | UAV por vuelo | canopy_cover                  |     0.84 |  0.59 |  0.92 |       8 |
| yellow_pea          | campo/curva   | NDVI_plotmean:auc             |     0.79 |  0.77 |  0.79 |       3 |
| yellow_pea          | campo/curva   | NDVI_plotmean:max_rate        |     0.77 |  0.77 |  0.77 |       1 |
| yellow_pea          | campo/curva   | NDVI_plotmean:senescence_rate |     0.7  |  0.7  |  0.7  |       1 |
| yellow_pea          | campo/curva   | NDVI_plotmean:ymax            |     0.4  |  0.36 |  0.44 |       2 |
| yellow_pea          | campo/curva   | canopy_cover:auc              |     0.81 |  0.78 |  0.83 |       2 |
| yellow_pea          | campo/curva   | canopy_cover:max_rate         |     0.48 |  0.48 |  0.48 |       1 |
| yellow_pea          | campo/curva   | canopy_cover:senescence_rate  |     0.41 |  0.41 |  0.41 |       1 |
| yellow_pea          | campo/curva   | canopy_cover:ymax             |     0.18 |  0.05 |  0.3  |       2 |
| yellow_pea          | campo/curva   | canopyht                      |     0.91 |  0.85 |  0.94 |       3 |
| yellow_pea          | campo/curva   | fiftyflowr                    |     0.96 |  0.95 |  0.97 |       5 |
| yellow_pea          | campo/curva   | physmatur                     |     0.85 |  0.81 |  0.96 |       5 |
| yellow_pea          | campo/curva   | seedyield                     |     0.81 |  0.78 |  0.94 |       3 |
| yellow_pea          | campo/curva   | vinelength                    |     0.86 |  0.84 |  0.95 |       3 |

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

## Correlaciones máximas (réplica)

| env            | market_class    | flight_dir                  |    gdd | target     | level    | feature        |      r |     p |   n |   absr |
|:---------------|:----------------|:----------------------------|-------:|:-----------|:---------|:---------------|-------:|------:|----:|-------:|
| 2019_Genesee   | kabuli_chickpea | Genesee_Pea_Chickpea_July05 |  787.4 | seedyield  | cultivar | canopy_area_m2 |  0.878 | 0     |  24 |  0.878 |
| 2018_Pullman   | yellow_pea      | Pullman_Pea_July27          | 1190.7 | physmatur  | cultivar | canopy_area_m2 |  0.859 | 0     |  41 |  0.859 |
| 2017_Fairfield | green_pea       | Fairfield_Pea_July24        | 1050   | seedyield  | cultivar | NDVI_mean      |  0.792 | 0     |  40 |  0.792 |
| 2017_Fairfield | green_pea       | Fairfield_Pea_July24        | 1050   | seedyield  | parcela  | GNDVI_sum      |  0.788 | 0     | 120 |  0.788 |
| 2017_Pullman   | kabuli_chickpea | Chickpea_Aug07              | 1377.8 | fiftyflowr | cultivar | NDRE_sum       |  0.776 | 0     |  24 |  0.776 |
| 2019_Genesee   | kabuli_chickpea | Genesee_Pea_Chickpea_July05 |  787.4 | seedyield  | parcela  | canopy_area_m2 |  0.774 | 0     |  72 |  0.774 |
| 2018_Pullman   | yellow_pea      | Pullman_Pea_July 19         | 1044.2 | fiftyflowr | cultivar | NDRE_mean      |  0.764 | 0     |  41 |  0.764 |
| 2018_Pullman   | yellow_pea      | Pullman_Pea_July27          | 1190.7 | physmatur  | parcela  | NDVI_sum       |  0.744 | 0     | 129 |  0.744 |
| 2017_Pullman   | kabuli_chickpea | Chickpea_Aug07              | 1377.8 | physmatur  | cultivar | TVI_sum        |  0.732 | 0     |  24 |  0.732 |
| 2018_Pullman   | green_pea       | Pullman_Pea_July27          | 1190.7 | fiftyflowr | cultivar | GNDVI_sum      |  0.655 | 0     |  59 |  0.655 |
| 2018_Pullman   | yellow_pea      | Pullman_Pea_July 19         | 1044.2 | fiftyflowr | parcela  | NDRE_mean      |  0.648 | 0     | 129 |  0.648 |
| 2017_Pullman   | kabuli_chickpea | Chickpea_Aug07              | 1377.8 | fiftyflowr | parcela  | TVI_sum        |  0.6   | 0     |  72 |  0.6   |
| 2017_Pullman   | kabuli_chickpea | Chickpea_Aug07              | 1377.8 | physmatur  | parcela  | TVI_sum        |  0.596 | 0     |  72 |  0.596 |
| 2017_Pullman   | yellow_pea      | Pea_June05                  |  284.3 | seedyield  | cultivar | NDRE_mean      | -0.584 | 0.003 |  24 |  0.584 |
| 2018_Pullman   | green_pea       | Pullman_Pea_July 19         | 1044.2 | fiftyflowr | parcela  | NDRE_mean      |  0.528 | 0     | 186 |  0.528 |
| 2017_Pullman   | green_pea       | Pea_July28                  | 1167.5 | physmatur  | parcela  | GNDVI_mean     |  0.519 | 0     | 154 |  0.519 |
| 2017_Fairfield | yellow_pea      | Fairfield_Pea_July24        | 1050   | seedyield  | parcela  | NDVI_sum       |  0.47  | 0     |  63 |  0.47  |
| 2018_Pullman   | green_pea       | Pullman_Pea_July27          | 1190.7 | physmatur  | cultivar | TVI_mean       |  0.468 | 0     |  59 |  0.468 |

## Fenología (CV por genotipo)

| crop     | target     |    n |   n_features |   r2_within_env |     r |    r2 |   rmse_days |   spearman |
|:---------|:-----------|-----:|-------------:|----------------:|------:|------:|------------:|-----------:|
| chickpea | fiftyflowr |  297 |           92 |           0.161 | 0.404 | 0.236 |       3.2   |      0.532 |
| chickpea | physmatur  |  297 |           92 |           0.016 | 0.17  | 0.317 |       5.537 |      0.533 |
| pea      | fiftyflowr | 1051 |           17 |           0.046 | 0.214 | 0.192 |       3.236 |      0.432 |
| pea      | physmatur  | 1053 |           17 |           0.025 | 0.161 | 0.257 |       3.919 |      0.613 |

## G×E

|   year | trial   | trait     |   n_env |   sigma_g |   sigma_ge |   sigma_e |   ratio_ge_g |   h2_multienv |
|-------:|:--------|:----------|--------:|----------:|-----------:|----------:|-------------:|--------------:|
|   2017 | 1701    | seedyield |       2 |   1609.38 |    13991.1 |   97953.4 |  8.693       |         0.065 |
|   2017 | 1701B   | seedyield |       2 |  13462.8  |    29247.2 |  152941   |  2.172       |         0.251 |
|   2017 | 1702    | seedyield |       2 |      0    |    41110.9 |  116315   |  1.37332e+09 |         0     |
|   2018 | 1801    | seedyield |       3 |  16256.9  |    11249.6 |   65892.6 |  0.692       |         0.595 |
|   2018 | 1802    | seedyield |       2 |  44872.2  |    24222.3 |   33762   |  0.54        |         0.717 |
|   2018 | 1881    | seedyield |       3 |  25642.6  |    26101.1 |   98931.8 |  1.018       |         0.566 |
|   2019 | 1901    | seedyield |       3 |  54470.3  |    20210.5 |   88654   |  0.371       |         0.767 |
|   2019 | 1901B   | seedyield |       2 |  54902.3  |    33493.2 |   65863.7 |  0.61        |         0.664 |
|   2019 | 1902    | seedyield |       2 |  30847.6  |    14374.1 |  102639   |  0.466       |         0.559 |
|   2019 | 1981    | seedyield |       3 |  45879.9  |    25455.3 |   70057.9 |  0.555       |         0.738 |

## Sensibilidad de la normalización (combinados)

| market_class    | dataset        | normalization     | variant   |   r2_parcela |   r2_parcela_sd |   n_selected |   r2_cultivar |   n_plots |   n_cultivars |   n_features |
|:----------------|:---------------|:------------------|:----------|-------------:|----------------:|-------------:|--------------:|----------:|--------------:|-------------:|
| kabuli_chickpea | 2018_combinado | dentro de sitio   | original  |        0.279 |           0.072 |         5    |         0.363 |       255 |            94 |           55 |
| kabuli_chickpea | 2018_combinado | dentro de sitio   | anidada   |        0.227 |           0.084 |         3.75 |         0.322 |       255 |            94 |           55 |
| kabuli_chickpea | 2018_combinado | conjunto agrupado | original  |        0.823 |           0.049 |         7    |         0.742 |       255 |            94 |           55 |
| kabuli_chickpea | 2018_combinado | conjunto agrupado | anidada   |        0.815 |           0.049 |        11.75 |         0.866 |       255 |            94 |           55 |
| kabuli_chickpea | 2019_combinado | dentro de sitio   | original  |        0.172 |           0.142 |         3    |         0.429 |       216 |            72 |           27 |
| kabuli_chickpea | 2019_combinado | dentro de sitio   | anidada   |        0.144 |           0.134 |         8.25 |         0.325 |       216 |            72 |           27 |
| kabuli_chickpea | 2019_combinado | conjunto agrupado | original  |        0.599 |           0.046 |         4    |         0.751 |       216 |            72 |           27 |
| kabuli_chickpea | 2019_combinado | conjunto agrupado | anidada   |        0.564 |           0.06  |         5.25 |         0.712 |       216 |            72 |           27 |
| green_pea       | 2017_combinado | dentro de sitio   | original  |        0.281 |           0.068 |         6    |       nan     |       156 |            49 |           66 |
| green_pea       | 2017_combinado | dentro de sitio   | anidada   |        0.174 |           0.165 |         2.5  |       nan     |       156 |            49 |           66 |
| green_pea       | 2017_combinado | conjunto agrupado | original  |        0.281 |           0.068 |         6    |       nan     |       156 |            49 |           66 |
| green_pea       | 2017_combinado | conjunto agrupado | anidada   |        0.174 |           0.165 |         2.5  |       nan     |       156 |            49 |           66 |
| green_pea       | 2018_combinado | dentro de sitio   | original  |        0.272 |           0.035 |         3    |         0.187 |       378 |           123 |           55 |
| green_pea       | 2018_combinado | dentro de sitio   | anidada   |        0.207 |           0.057 |         7    |         0.1   |       378 |           123 |           55 |
| green_pea       | 2018_combinado | conjunto agrupado | original  |        0.719 |           0.016 |         7    |         0.837 |       378 |           123 |           55 |
| green_pea       | 2018_combinado | conjunto agrupado | anidada   |        0.707 |           0.028 |        15    |         0.802 |       378 |           123 |           55 |
| green_pea       | 2019_combinado | dentro de sitio   | original  |        0.251 |           0.142 |         8    |       nan     |       261 |            87 |           27 |
| green_pea       | 2019_combinado | dentro de sitio   | anidada   |        0.218 |           0.125 |        11.75 |       nan     |       261 |            87 |           27 |
| green_pea       | 2019_combinado | conjunto agrupado | original  |        0.751 |           0.043 |        10    |         0.774 |       261 |            87 |           27 |
| green_pea       | 2019_combinado | conjunto agrupado | anidada   |        0.761 |           0.043 |        13.25 |         0.743 |       261 |            87 |           27 |
| yellow_pea      | 2017_combinado | dentro de sitio   | original  |        0.086 |           0.197 |         4    |       nan     |        81 |            25 |           66 |
| yellow_pea      | 2017_combinado | dentro de sitio   | anidada   |        0.071 |           0.193 |         2.5  |        -0.275 |        81 |            25 |           66 |
| yellow_pea      | 2017_combinado | conjunto agrupado | original  |        0.086 |           0.197 |         4    |       nan     |        81 |            25 |           66 |
| yellow_pea      | 2017_combinado | conjunto agrupado | anidada   |        0.071 |           0.193 |         2.5  |        -0.275 |        81 |            25 |           66 |
| yellow_pea      | 2018_combinado | dentro de sitio   | original  |        0.218 |           0.017 |         4    |         0.174 |       198 |            64 |           55 |
| yellow_pea      | 2018_combinado | dentro de sitio   | anidada   |        0.134 |           0.101 |         5.25 |         0.174 |       198 |            64 |           55 |
| yellow_pea      | 2018_combinado | conjunto agrupado | original  |        0.335 |           0.049 |         4    |         0.24  |       198 |            64 |           55 |
| yellow_pea      | 2018_combinado | conjunto agrupado | anidada   |        0.245 |           0.143 |         5.25 |         0.261 |       198 |            64 |           55 |
| yellow_pea      | 2019_combinado | dentro de sitio   | original  |      nan     |         nan     |         0    |       nan     |       138 |            46 |            5 |
| yellow_pea      | 2019_combinado | dentro de sitio   | anidada   |       -0.112 |           0     |         0.25 |       nan     |       138 |            46 |            5 |
| yellow_pea      | 2019_combinado | conjunto agrupado | original  |        0.252 |           0.089 |         1    |         0.381 |       138 |            46 |            5 |
| yellow_pea      | 2019_combinado | conjunto agrupado | anidada   |        0.247 |           0.076 |         1.75 |         0.382 |       138 |            46 |            5 |

## Rasgos absolutos vs estandarizados (entre ambientes)

| crop   | scheme   | features             | model         | test_env       |      r2 |     rmse |   spearman |   top20 |
|:-------|:---------|:---------------------|:--------------|:---------------|--------:|---------:|-----------:|--------:|
| pea    | ambiente | sin imágenes (media) | nulo          | 2017_Fairfield |  -0.004 |  644.124 |    nan     |   0.354 |
| pea    | ambiente | z                    | Random Forest | 2017_Fairfield |  -0.318 |  738.217 |    nan     |   0.354 |
| pea    | ambiente | z                    | XGBoost       | 2017_Fairfield |  -0.331 |  741.617 |    nan     |   0.354 |
| pea    | ambiente | abs                  | Random Forest | 2017_Fairfield |  -0.018 |  648.792 |    nan     |   0.354 |
| pea    | ambiente | abs                  | XGBoost       | 2017_Fairfield |  -0.017 |  648.345 |    nan     |   0.354 |
| pea    | ambiente | abs+z                | Random Forest | 2017_Fairfield |  -0.018 |  648.83  |    nan     |   0.354 |
| pea    | ambiente | abs+z                | XGBoost       | 2017_Fairfield |  -0.006 |  644.943 |    nan     |   0.354 |
| pea    | ambiente | sin imágenes (media) | nulo          | 2017_Pullman   | -18.693 | 1273.5   |    nan     |   0.085 |
| pea    | ambiente | z                    | Random Forest | 2017_Pullman   | -38.422 | 1801.84  |     -0.052 |   0.085 |
| pea    | ambiente | z                    | XGBoost       | 2017_Pullman   | -35.652 | 1737.39  |     -0.15  |   0.085 |
| pea    | ambiente | abs                  | Random Forest | 2017_Pullman   | -11.48  | 1013.81  |      0.033 |   0.237 |
| pea    | ambiente | abs                  | XGBoost       | 2017_Pullman   | -13.723 | 1101.13  |      0.057 |   0.169 |
| pea    | ambiente | abs+z                | Random Forest | 2017_Pullman   | -12.375 | 1049.54  |      0.111 |   0.254 |
| pea    | ambiente | abs+z                | XGBoost       | 2017_Pullman   |  -9.355 |  923.486 |      0.058 |   0.237 |
| pea    | ambiente | sin imágenes (media) | nulo          | 2018_Fairfield |  -0.017 |  309.425 |    nan     |   0.303 |
| pea    | ambiente | z                    | Random Forest | 2018_Fairfield |  -1.314 |  466.804 |      0.191 |   0.152 |
| pea    | ambiente | z                    | XGBoost       | 2018_Fairfield |  -1.233 |  458.468 |      0.089 |   0.212 |
| pea    | ambiente | abs                  | Random Forest | 2018_Fairfield |  -3.665 |  662.729 |      0.241 |   0.152 |
| pea    | ambiente | abs                  | XGBoost       | 2018_Fairfield |  -2.637 |  585.177 |      0.188 |   0.303 |
| pea    | ambiente | abs+z                | Random Forest | 2018_Fairfield |  -4.865 |  743.122 |      0.277 |   0.121 |
| pea    | ambiente | abs+z                | XGBoost       | 2018_Fairfield |  -2.919 |  607.397 |      0.145 |   0.091 |
| pea    | ambiente | sin imágenes (media) | nulo          | 2018_Genesee   |  -8.888 | 1438.06  |    nan     |   0.263 |
| pea    | ambiente | z                    | Random Forest | 2018_Genesee   | -22.157 | 2200.75  |      0.124 |   0.263 |
| pea    | ambiente | z                    | XGBoost       | 2018_Genesee   | -20.387 | 2114.94  |      0.194 |   0.263 |
| pea    | ambiente | abs                  | Random Forest | 2018_Genesee   |  -6.425 | 1246.21  |      0.008 |   0.263 |
| pea    | ambiente | abs                  | XGBoost       | 2018_Genesee   |  -7.695 | 1348.53  |      0.265 |   0.263 |
| pea    | ambiente | abs+z                | Random Forest | 2018_Genesee   |  -4.974 | 1117.83  |      0.16  |   0.316 |
| pea    | ambiente | abs+z                | XGBoost       | 2018_Genesee   |  -4.583 | 1080.58  |      0.36  |   0.158 |
| pea    | ambiente | sin imágenes (media) | nulo          | 2018_Pullman   |  -1.38  |  496.882 |    nan     |   0.159 |
| pea    | ambiente | z                    | Random Forest | 2018_Pullman   |  -0.437 |  386.09  |      0.086 |   0.286 |
| pea    | ambiente | z                    | XGBoost       | 2018_Pullman   |  -0.772 |  428.744 |      0.123 |   0.254 |
| pea    | ambiente | abs                  | Random Forest | 2018_Pullman   |  -1.041 |  460.135 |      0.226 |   0.27  |
| pea    | ambiente | abs                  | XGBoost       | 2018_Pullman   |  -0.928 |  447.224 |      0.184 |   0.27  |
| pea    | ambiente | abs+z                | Random Forest | 2018_Pullman   |  -1.923 |  550.641 |      0.261 |   0.333 |
| pea    | ambiente | abs+z                | XGBoost       | 2018_Pullman   |  -2.603 |  611.306 |      0.229 |   0.254 |
| pea    | ambiente | sin imágenes (media) | nulo          | 2019_Fairfield |  -0.441 |  515.632 |    nan     |   0.194 |
| pea    | ambiente | z                    | Random Forest | 2019_Fairfield |  -0.085 |  447.391 |      0.123 |   0.323 |
| pea    | ambiente | z                    | XGBoost       | 2019_Fairfield |  -0.339 |  497.024 |      0.06  |   0.129 |
| pea    | ambiente | abs                  | Random Forest | 2019_Fairfield |  -0.425 |  512.75  |     -0.034 |   0.161 |
| pea    | ambiente | abs                  | XGBoost       | 2019_Fairfield |  -0.413 |  510.522 |     -0.038 |   0.226 |
