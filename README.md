# pea_drone — Fenotipado UAV multiespectral de arveja y garbanzo (2017-2019)

Réplica y extensión de **Zhang et al. (2021)**, *Crop performance evaluation of chickpea and dry pea breeding
lines across seasons and locations using phenomics data*, Front. Plant Sci. 12:640259
([doi:10.3389/fpls.2021.640259](https://doi.org/10.3389/fpls.2021.640259)), con referencia metodológica a
**Marzougui et al. (2023)**, Front. Plant Sci. 14:1111575 ([doi:10.3389/fpls.2023.1111575](https://doi.org/10.3389/fpls.2023.1111575)).

Datos: ensayos de mejoramiento de arveja (*Pisum sativum*) y garbanzo (*Cicer arietinum*) del USDA-ARS / Washington
State University en Pullman (WA), Fairfield (WA) y Genesee (ID), registrados con UAV + MicaSense RedEdge (5 bandas).

## Objetivos
1. Reproducir el procesamiento y los resultados de Zhang et al. (2021): correlaciones entre rasgos UAV y rendimiento/fenología, y regresión LASSO.
2. Ir más allá:
   - dinámica temporal en grados-día;
   - heredabilidad y G×E de rasgos UAV;
   - índices fisiológicos nuevos (clorofila, flores, senescencia);
   - modelos de ML/DL con validación entre ambientes.
3. Análisis por material: arveja verde, amarilla y verde-amarilla NZ; garbanzo kabuli y verde.

## Estructura
```
pipeline/            scripts numerados, uno por paso (ejecutar en orden)
  config.py          rutas, bandas y parseo de nombres de archivo
  01_inventory_images.py    inventario y QC de ortomosaicos
  02_qc_tabular.py          consolidación y QC de datos de campo
  03_spectral_histograms.py histogramas y firmas espectrales (DN sin calibrar)
docs/
  WORKFLOW.md        hoja de ruta metodológica completa (fases 0-7)
  DATA_ISSUES.md     registro de problemas de datos y decisiones tomadas
outputs/             resultados de cada paso (tablas, figuras, reportes)
```

## Reproducir
```bash
pip install -r requirements.txt
python pipeline/01_inventory_images.py
python pipeline/02_qc_tabular.py
python pipeline/03_spectral_histograms.py
```
Los datos crudos (ortomosaicos `Images20NN/`, `20NNPulseDataset.xlsx`, `PulsePlotMaps_2017-2019.pdf`) no se versionan.
Se colocan en la raíz del repositorio con la misma estructura de carpetas.

## Estado
| Fase | Descripción | Estado |
|---|---|---|
| 1 | Inventario y QC (imágenes, campo, respuesta espectral) | ✅ |
| 1b | Mapas de contexto de los sitios | en curso |
| 2 | Calibración radiométrica, corregistro, grilla de parcelas, segmentación | en curso |
| 3-6 | Rasgos, réplica, temporal y genética, ML/DL | pendiente |
| 7 | Manuscrito | pendiente |

## Créditos de datos
Ensayos e imágenes: R. J. McGee, G. J. Vandemark (USDA-ARS Grain Legume Genetics and Physiology Research Unit),
S. Sankaran y C. Zhang (WSU Biological Systems Engineering). Análisis de este repositorio: J. E. Flores-Riera (UNAL).
