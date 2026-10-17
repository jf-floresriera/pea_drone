# Cola de trabajo (roadmap)

Estado al 2026-10-17 (pipeline completo). ✅ hecho · 🔄 en curso · ⏳ en cola · 🔒 depende de los autores (WSU/USDA-ARS).
Cada paso es un script numerado en `pipeline/` con salidas en `outputs/` y se sube a GitHub al completarse.

## Fase 1 - Inventario y calidad ✅
- ✅ Inventario de 275 ortomosaicos (`01`), QC de datos de campo (`02`), respuesta espectral sin calibrar (`03`)
- ✅ Mapas de contexto: localización, campos y calendario de vuelos (`04`)
- ✅ Registro de problemas de datos y decisiones (`docs/DATA_ISSUES.md`)

## Fase 2 - Preprocesamiento geomático
- ✅ 2.2 Calibración radiométrica cruzada con Sentinel-2 por sectores (`05`), 55/55 vuelos, R² 0,80-0,96
- ✅ 2.4a Digitalización de croquis: 34/34 ensayos, 2415 parcelas, validado 1:1 con el Excel (`06`)
- ✅ 2.4b Georreferenciación de la grilla registrando la captura del croquis contra el mosaico (`07`)
- ✅ 2.4c Verificación y refinamiento afín de la grilla (contraste vegetación dentro/calle) (`07b`)
- ✅ 2.3 Corregistro multitemporal (`09`; refinamiento por vuelo en los ejes de la grilla, 4 vuelos ambiguos excluidos)
- ✅ 2.5 Máscara de dosel por Otsu sobre SAVI calibrado (`10`) · ⏳ opcional: clasificador con clase flor de arveja
- 🔒 Calibración de referencia con panel sobre imágenes crudas (requiere crudos + panel)

## Fase 3 - Rasgos por parcela y fecha ✅ (`08_weather_gdd.py`, `10_features.py`; 8079 parcela × vuelo)
- Reflectancia calibrada (coeficientes de `05`) en cada polígono con recorte de bordes
- Índices de la réplica: NDVI, GNDVI, SAVI, NDRE, TVI (media y suma); cobertura del dosel
- Índices nuevos: CIred-edge, CIgreen, OSAVI, EVI2, MCARI, MTCI aproximado, NDRE/NDVI; percentiles y CV
- Textura GLCM sobre NIR y NDVI; fracción de flor (arveja)
- Grados-día acumulados (base 3 °C) con datos diarios de gridMET/Daymet por sitio (`10a_weather.py`)
- Tabla larga `plot_date_features.parquet` (parcela × fecha × rasgo) + tabla ancha por parcela

## Fase 4 - Réplica de Zhang et al. (2021) ✅ (`11`; `11b` sensibilidad de la normalización)
- Correlaciones de Pearson parcela a parcela y por cultivar (media de 3 rep.) con rendimiento, días a floración y madurez
- LASSO (α = 1, CV 5 × 3, rasgos seleccionados en ≥75 % de corridas, partición 3:1 × 4, LOO por cultivar)
- Tabla comparativa contra los valores publicados

## Fase 5 - Más allá de la réplica ✅ (`12`, `13`, `14`)
- `12_temporal.py`: curvas logísticas o P-splines de cobertura e índices contra grados-día; parámetros
  (máximo, tasa, inflexión, AUC, senescencia)
- `13_mixed_models.py`: modelos mixtos con efectos espaciales (SpATS) → BLUEs/BLUPs, H² de Cullis por fecha y por
  parámetro de curva, correlaciones genéticas con el rendimiento, G×E multiambiente, coincidencia de selección
- `14_phenology.py`: fecha de 50 % de floración (fracción de flor) y madurez (senescencia) desde el aire, validadas
  con `fiftyflowr` y `physmatur`
- Análisis por material: arveja verde, amarilla, NZ verde-amarilla, garbanzo kabuli y verde

## Fase 6 - Modelos de ML/DL ✅ (`15`; `15b` rasgos absolutos vs estandarizados)
- Línea base: LASSO, Elastic Net, PLSR · Árboles: RF, XGBoost · Temporal: 1D-CNN / LSTM / TempCNN ·
  Imagen: CNN multitemporal sobre recortes de parcela
- Validación: parcela aleatoria → genotipo excluido → ambiente (sitio-año) excluido → año futuro
- Interpretabilidad (SHAP/permutación) y costo computacional (CodeCarbon)

## Fase 7 - Manuscrito ⏳
- ✅ Borrador completo en `docs/MANUSCRIPT.md` (resumen, introducción, métodos, resultados, discusión, conclusiones)
- ✅ Figuras (22) y tablas (5) en `outputs/16_manuscript/` (`16`)
- ⏳ Revisión por coautores, formato de la revista, Zenodo con DOI

## Pendiente de los autores 🔒
1. Los 34 `.tif` vacíos (Pullman 2019 completo; red edge de garbanzo Pullman 2017)
2. Imágenes crudas de la cámara y fotos del panel de reflectancia (y su certificado de reflectancia)
3. Reportes de procesamiento de Pix4D (GCP, RMS, calibración de cámara)
4. Opcional: metadatos de genotipos (tipo de hoja, pedigrí, marcadores)
5. Autorización explícita para publicar los datos de campo en un repositorio público (Zenodo/GitHub)

## Extensiones opcionales (no bloquean el artículo)
- Modelos espaciales con P-splines (SpATS, R) y H² de Cullis
- Detección de flores de arveja a alta resolución para fenología
- CNN sobre recortes de imagen por parcela
- Análisis de sensibilidad excluyendo los campos de confianza media (GRID-02)
