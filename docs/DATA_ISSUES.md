# Registro de problemas de datos y decisiones

Cada entrada indica dónde se detectó el problema, el efecto que tiene y la decisión tomada. La evidencia automática está en
`outputs/01_inventory/inventory_summary.md` y `outputs/02_tabular_qc/qc_issues.csv`.

## Imágenes

| ID | Problema | Efecto | Decisión |
|---|---|---|---|
| IMG-01 | 34 `.tif` de 0 bytes | Pullman 2019: avanzados 6/17 (solo NIR y R), 7/05 y 7/16, y todo el preliminar (6/17, 7/05, 7/17). Garbanzo Pullman 2017: sin red edge en 5 fechas y sin verde el 7/21 | Se sigue con lo disponible: cada índice se calcula solo donde existen sus bandas. Se pide a los autores la copia completa |
| IMG-02 | Mosaicos en DN (12 bit × 16, máx. 65520), no en reflectancia. Evidencia en el dosel denso (Pullman 2018-07-19 y Genesee 2018-07-23): azul 0,27-0,32 (real ≈0,03), NIR/R 2,9-3,6 (real ≥8) y NDVI 0,48-0,56 (real ≈0,85). En el suelo: NDVI −0,22 (real +0,1 a +0,25). Dianas blancas saturadas | Índices no comparables entre fechas o sitios; TVI y SAVI sesgados | Calibración radiométrica (Fase 2.2, `RADIOMETRIC_METHODS.md`) |
| IMG-03 | 5 archivos sin canal alfa (1 banda) | Máscara de mosaico | DN = 0 se toma como fuera del mosaico |
| IMG-04 | Costuras radiométricas visibles en mosaicos CIR | Gradientes dentro del campo | Normalización y efecto de bloque en los modelos mixtos |
| IMG-05 | Mosaicos de Fairfield rotulados `PeaLentil` | Contienen ensayos de lenteja | Se excluyen mediante la grilla de parcelas |
| IMG-06 | La carpeta `Preliminary_July16` (2019) contiene archivos rotulados `Jun16` | Fecha ambigua | Se usa la fecha 2019-07-17 de la hoja Description (`config.py`) |

## Datos de campo

| ID | Problema | Decisión |
|---|---|---|
| FLD-01 | `seedyield` rotulado g/ha; los valores son kg/ha (yieldlbs = seedyield × 0,892) | Se reporta en kg/ha |
| FLD-02 | Fenología de Fairfield 2017 (1701, 1701B, 1702) idéntica a la de Pullman | **Decisión del equipo (2026-10-16): se asumen válidos los datos fisiológicos tal como fueron entregados.** Se documenta, pero no se excluyen |
| FLD-03 | Description 2018: 1881 Genesee rotulado "Advanced Green Pea" | El código x8x es garbanzo (las entradas SR, RY, … son garbanzo). Se usa `crop` según el código |
| FLD-04 | 1804 Pullman 2018: 60 parcelas en la hoja vs. 20 en Description | Se usan las 60 de la hoja (20 entradas × 3 rep.) |
| FLD-05 | 1883 Pullman 2018: 33 entradas × 2 rep. vs. 22 × 3 en Description | Se usa la hoja. El análisis mixto admite el desbalance |
| FLD-06 | 1803/1804 Pullman 2018 sin columna de bloque | Bloque inferido por la secuencia de parcela, verificado balanceado (`block_inferred = True`) |
| FLD-07 | Nombres de columnas inconsistentes (`bloc`, `slotseedwt`, `entry` en lugar de `record`, columnas duplicadas) | Normalizados en `02_qc_tabular.py` |
| FLD-08 | Hojas de Pullman 2019 desordenadas | Se ordena por número de parcela |
| FLD-09 | Description trae un solo GPS por sitio-año, pero en Fairfield el garbanzo está en **otro campo**: a ~6 km al N de la arveja en 2018 y a ~2 km al O en 2019 (verificado con los ortomosaicos) | La ubicación de cada campo se toma del centroide del mosaico (`outputs/04_context/mosaic_footprints.geojson`). La rotación de parcelas ya era distinta por ensayo |

## Croquis (PulsePlotMaps_2017-2019.pdf)

| ID | Problema | Decisión |
|---|---|---|
| MAP-01 | Errores de digitación: Pullman 2018 F1-C6 "35" (va 55); Fairfield 2018 "36" repetido en C5; Fairfield 2019 F2 en otro orden | Al construir la grilla se valida que cada parcela aparezca una sola vez y se corrige por secuencia |
