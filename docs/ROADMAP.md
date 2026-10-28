# Cola de trabajo (roadmap)

**Autor:** Jesús Enrique Flores Riera — candidato a Maestría en Geomática, Universidad Nacional de Colombia
(jfloresr@unal.edu.co).

Estado al **2026-10-19**: pipeline completo (01 → 16) con figuras y tablas de resultados.
✅ hecho · ⏳ pendiente · 🔒 depende de los autores de los datos (WSU/USDA-ARS) · ➕ extensión opcional.
Cada paso es un script numerado en `pipeline/` con salidas en `outputs/`.

## Fase 1 - Inventario y calidad ✅
- ✅ Inventario de 275 ortomosaicos (`01`); los 34 archivos vacíos se descartaron
- ✅ QC de los datos de campo (`02`) y respuesta espectral sin calibrar (`03`)
- ✅ Mapas de contexto: localización, campos y calendario de vuelos (`04`)
- ✅ Registro de problemas de datos y decisiones (`docs/DATA_ISSUES.md`)

## Fase 2 - Preprocesamiento geomático ✅
- ✅ Calibración radiométrica cruzada con Sentinel-2 L2A por sectores (`05`), en 55/55 vuelos
  - Modelo adoptado: ganancia por el origen (M3), elegido por plausibilidad física
  - R² agrupado de 0,59-0,96 (el verde de 2017 no se ajusta)
- ✅ Digitalización de croquis (`06`): 34/34 ensayos y 2415 parcelas, validados 1:1 con el Excel
- ✅ Georreferenciación de la grilla (`07`) y refinamiento afín con prior físico (`07b`)
- ✅ Corregistro multitemporal (`09`): refinamiento por vuelo en los ejes de la grilla; 4 vuelos ambiguos excluidos
- ✅ Máscara de dosel por Otsu sobre SAVI calibrado (en `10`)
- 🔒 Calibración de referencia con panel sobre imágenes crudas (requiere los crudos y el panel)

## Fase 3 - Rasgos por parcela y fecha ✅
- ✅ Clima diario Daymet V4 y grados-día con base 3 °C (`08`)
- ✅ Rasgos por parcela y vuelo (`10`): 8079 registros, 2172 parcelas y 46 vuelos
  - Índices: NDVI, GNDVI, SAVI, NDRE, TVI, OSAVI, EVI2, MCARI, CIgreen, CIred-edge y MTCI
  - Cobertura y área de dosel
  - Percentiles y CV
  - Textura GLCM del NIR

## Fase 4 - Réplica de Zhang et al. (2021) ✅
- ✅ Correlaciones por parcela y por cultivar; LASSO en versión original y anidada, sin fuga (`11`)
- ✅ Sensibilidad a la normalización de los conjuntos combinados (`11b`)

## Fase 5 - Más allá de la réplica ✅
- ✅ Curvas logísticas en grados-día y parámetros: inflexión, tasa, AUC, máximo y senescencia (`12`)
- ✅ Modelos mixtos (`13`):
  - bloque y tendencias de fila/columna;
  - H² en base a medias de genotipo;
  - correlación entre valores genotípicos y rendimiento;
  - coincidencia de selección;
  - G×E.
- ✅ Fenología desde el aire, con CV agrupada por genotipo (`14`)

## Fase 6 - Machine Learning / Deep Learning ✅
- ✅ LASSO, Elastic Net, PLSR, Random Forest, XGBoost y TempCNN con 4 esquemas de validación (`15`)
- ✅ Importancia por permutación y TreeSHAP (API nativa de XGBoost); tiempos de cómputo
- ✅ Rasgos absolutos calibrados vs. estandarizados para predecir entre ambientes (`15b`)

## Fase 7 - Figuras y tablas de resultados ✅
- ✅ 22 figuras y 5 tablas en `outputs/16_figures/`, más `RESULTS_SUMMARY.md` (`16`)

## ⏳ Pendiente
**Gestión de datos:**
1. Decidir si los datos de campo (Excel y croquis) se publican en el repositorio o en Zenodo. Requiere la autorización
   escrita de WSU/USDA-ARS (ver 🔒).

**Técnico:**
2. Análisis de sensibilidad excluyendo los campos de confianza media (GRID-02: Pullman 2017 arveja y Genesee 2018).
3. Exportar figuras en TIFF a 300-600 dpi.
4. Depositar código y tablas derivadas en Zenodo con DOI.

## 🔒 Pendiente de los autores de los datos
1. Los 34 `.tif` vacíos (Pullman 2019; red edge del garbanzo de Pullman 2017)
2. Imágenes crudas de la cámara y fotos del panel de reflectancia (con su certificado)
3. Reportes de procesamiento de Pix4D (GCP, RMS, calibración de cámara)
4. Opcional: metadatos de genotipos (tipo de hoja, pedigrí, marcadores)
5. Autorización explícita para publicar los datos de campo

## ➕ Extensiones opcionales
- Modelos espaciales con P-splines (SpATS, en R) y H² de Cullis
- Detección de flores de arveja a alta resolución para mejorar la fenología
- CNN sobre recortes de imagen por parcela
