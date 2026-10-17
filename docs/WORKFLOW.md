# Flujo de trabajo: fenotipado UAV multiespectral de arveja y garbanzo (WSU/USDA-ARS, 2017-2019)

**Objetivo del artículo.** Replicar Zhang et al. (2021, *Front. Plant Sci.* 12:640259) y extenderlo en cuatro
direcciones: (1) dinámica temporal del dosel en función de grados-día, (2) parámetros genéticos de los rasgos UAV
(heredabilidad, correlaciones genéticas, G×E), (3) nuevos rasgos fisiológicos (índices de clorofila, flores, senescencia)
y (4) modelos de ML/DL evaluados con validación entre ambientes. Referencia metodológica secundaria:
Marzougui et al. (2023, *Front. Plant Sci.* 14:1111575): Random Forest con holdout por entrada e importancia por permutación.

**Principio de trabajo.** Se procede como si se partiera de cero. Cada paso queda en un script numerado (`pipeline/NN_*.py`)
con salidas en `outputs/NN_*/`, de modo que el artículo completo se pueda reproducir desde los datos crudos.

---

## 0. Datos de entrada

| Fuente | Contenido | Estado |
|---|---|---|
| `Images2017/…Images2019/` | 55 vuelos × 5 bandas (B, G, R, RE, NIR), ortomosaicos Pix4D `transparent_mosaic`, UTM 11N | 241/275 archivos OK, 34 vacíos (0 bytes) |
| `20NNPulseDataset.xlsx` | Hoja `Description` (ensayo, GPS, rotación de parcelas, fechas UAV) + una hoja por ensayo con datos por parcela | 2415 parcelas, 34 ensayos |
| `PulsePlotMaps_2017-2019.pdf` | Croquis fila × columna de cada sitio-año sobre el mosaico (13 páginas) | Completo; tiene errores de digitación (ver 1.3) |

### Faltantes (pedir, descargar o justificar)

| # | Archivo | Para qué | Prioridad |
|---|---|---|---|
| 1 | Los 34 `.tif` vacíos (lista en `outputs/01_inventory/inventory_summary.md`) | Pullman 2019 (único sitio con fenología ese año) queda con 1 fecha útil; garbanzo Pullman 2017 sin red edge (sin NDRE) | **Crítica** |
| 2 | Valores de reflectancia del panel (MicaSense 2017; Spectralon 99 % en 2018-19) y fotos o coordenadas del panel en cada vuelo | Calibración radiométrica (los mosaicos están en DN, no en reflectancia) | **Crítica** |
| 3 | Reportes de calidad de Pix4D (`*_report.pdf`), o al menos la versión, plantilla y uso de GCP | Documentar la ortorrectificación y el mosaico | Alta |
| 4 | Datos meteorológicos diarios (Tmín/Tmáx) por sitio | Grados-día (base 3 °C, como en Zhang 2021). Se descargan de gridMET/Daymet (abiertos) o AgWeatherNet | Alta (se puede obtener) |
| 5 | PDFs y material suplementario de los dos artículos (Tabla 1: altitud y hora de cada vuelo) | Documentar la adquisición y comparar resultados | Media |
| 6 | Información de los genotipos (tipo de hoja: semiáfila o normal; kabuli; pedigrí; marcadores si existen) | Análisis de diferenciación genética y GWAS opcional | Media |

---

## 1. Inventario y calidad de datos (FASE 1, implementada)

Scripts: `01_inventory_images.py`, `02_qc_tabular.py`, `03_spectral_histograms.py`.

### 1.1 Imágenes
- Integridad, CRS, GSD (1,4-3,2 cm), extensión, banda alfa, saturación y percentiles de DN por archivo
  (`image_inventory.csv`), y completitud de bandas por vuelo (`flight_inventory.csv`).
- **Estado radiométrico:** DN de 12 bit × 16 (máximo 65520), con medianas similares en las cinco bandas.
  No son reflectancia, así que la calibración es obligatoria (Fase 2.2).
- En cada vuelo las cinco bandas comparten la misma grilla (ancho, alto y origen idénticos), por lo que no hace
  falta corregistrar bandas entre sí.
- Hay 5 archivos de 1 sola banda (sin alfa): azul de Fairfield 2017-07-24, 2018-06-29, 2018-08-07 y 2019-06-10,
  y verde de Genesee 2018-08-06. Se trata DN = 0 como fuera del mosaico.
- Los mosaicos de arveja de Fairfield se llaman `PeaLentil`: cubren también ensayos de lenteja, que deben excluirse con la grilla.
- Evidencia de falta de calibración (Fase 1c, `outputs/03_spectral/`):
  - umbral Otsu de NDVI con DN de 0,02-0,27 (con reflectancia: ≈0,3-0,4);
  - firma del suelo casi plana y más brillante que la vegetación en el rojo;
  - costuras de color visibles en los mosaicos CIR (`quicklook/`).

### 1.2 Datos de campo
- Tabla maestra `plots_master.csv`, con identificador `plot_uid = año_sitio_ensayo_Pnnn`.
- Conteos vs. Description, balance de repeticiones, faltantes por rasgo, atípicos de rendimiento (z robusto > 3,5)
  y repetibilidad H² del rendimiento y de la fenología por ensayo (`trial_counts.csv`).
- Problemas detectados (`qc_issues.csv`):
  - `seedyield` está rotulado en g/ha, pero los valores son **kg/ha** (yieldlbs = seedyield × 0,892).
  - La fenología de Fairfield 2017 es idéntica a la de Pullman. **Decisión del equipo: los datos fisiológicos se asumen válidos tal como se entregaron** (ver `DATA_ISSUES.md`, FLD-02).
  - En Description, el 1881 de Genesee 2018 figura como arveja, pero es garbanzo.
  - 1804 Pullman 2018: 60 parcelas en la hoja vs. 20 en Description. 1883: 33 entradas × 2 rep. vs. 22 × 3.
  - 1803/1804 Pullman 2018 no traen columna de bloque. Se infirió por secuencia de parcela y se verificó el balance.

### 1.3 Croquis de parcelas
- Hay errores de digitación en el PDF (p. ej., Pullman 2018 F1-C6 dice "35" donde va "55"; Fairfield 2018 tiene un "36"
  repetido; Fairfield 2019 F2 tiene el orden alterado). Cada matriz se valida contra la lista de parcelas del Excel
  (cada número de parcela debe aparecer una sola vez por ensayo).

### 1.4 Material principal
| | Parcelas con campo | Parcelas con ≥3 fechas completas | Rasgos además del rendimiento |
|---|---|---|---|
| **Arveja** (paneles 01, 01B, 02, 03, 04) | 1776 | ≈1160 | Pullman 2017-2018 |
| Garbanzo (81, 81G, 83) | 639 | ≈400 (+96 de 2017 sin red edge) | Pullman 2017-2018 |

Decisión: la **arveja** es el cultivo principal (más parcelas, más entradas y más ambientes); el garbanzo sirve de
validación cruzada entre especies. El **2018** es el año núcleo: 3 sitios × 4-5 fechas, bandas completas y GSD ≈ 1,7 cm.

---

## 2. Preprocesamiento geomático (FASE 2)

### 2.1 Documentación de lo ya hecho (no se rehace)
- Adquisición: UAV AgBot (ATI) + MicaSense RedEdge, 25/30/45 m sobre el terreno, 2-3 m/s, solape 80/70 %,
  entre las 10:00 y las 15:00 (Zhang 2021).
- Procesamiento: Pix4Dmapper, plantilla *Ag Multispectral*, con ortomosaico por banda y canal alfa.
  Se verifica a partir de los archivos: UTM 11N (EPSG:32611), GSD real por vuelo y compresión LZW sin teselas ni pirámides.
- Si se obtienen los reportes de Pix4D (faltante 3), se tabulan el RMS de reproyección, el número de imágenes
  calibradas y el uso de GCP.

### 2.2 Calibración radiométrica (se rehace) → `05_radiometric_calibration.py`
**Diagnóstico (2026-10-16).** Se buscaron paneles en los mosaicos (objetos pequeños, homogéneos y brillantes en las
5 bandas). Solo aparecen **dianas GCP** (tableros blancos y damas blanco/negro), que confirman que la ortorrectificación
usó puntos de control. Los blancos están **saturados** (DN ≈ 65520) en 2018-2019 y varían entre vuelos en 2017.
El panel de reflectancia (MicaSense 2017, Spectralon 99 % en 2018-19) no está en los mosaicos: se fotografió en tierra.

**Método adoptado: línea empírica cruzada con Sentinel-2 L2A y muestreo por sectores** (Planetary Computer):
1. Para cada vuelo, se toma la escena S2 más cercana (|Δt| ≤ 6 d) con ≥95 % de la huella en las clases SCL 4/5.
2. **Desajuste de escala (2 cm vs. 10-20 m).** La comparación píxel a píxel dio R² de 0,0-0,6 por:
   - el error de geolocalización de S2;
   - la PSF del sensor MSI;
   - la mezcla parcela/calle en los bordes.
   Se reemplazó por un **muestreo por sectores**:
   - Sector = celda de 20 m de la grilla S2 (2×2 píxeles de 10 m; 1 píxel de B05).
   - El UAV se lleva a 2 m y se convoluciona con una gaussiana que imita la PSF de S2 (σ = 4 m en las bandas de 10 m
     y 8 m en B05); luego se promedia por sector.
   - Se busca el desfase UAV-S2 en ±20 m que maximiza la correlación NIR+rojo (se halló, p. ej., 10 m en Pullman 2018).
   - Se usan solo sectores con cobertura UAV completa, SCL 4/5 y CV interno del NIR ≤ 0,25.
   - Los sectores se estratifican en suelo, mezcla y dosel según el NDVI de S2.
   Resultado en Pullman 2018-07-19: R² de 0,85-0,93 en azul, rojo y NIR (antes ≈0,1-0,4).
3. **Ajuste agrupado por año y banda:** ρ = b(año, banda) + g(vuelo, banda)·DN, con Huber robusto.
   - El offset b (nivel de negro del sensor) es común a los vuelos del año y la ganancia g es propia de cada vuelo.
   - Al combinar fechas se amplía el rango (suelo en junio, dosel en julio) y el offset queda identificado,
     incluso en vuelos tempranos de bajo contraste.
4. Validación física independiente: NDVI de dosel y suelo y reflectancia del rojo y del NIR del dosel, en rangos esperables.
5. Se guardan los coeficientes (`calibration_coefficients.csv`) y se aplican al extraer rasgos.
   No se escriben mosaicos calibrados por falta de disco.
6. Limitaciones a declarar:
   - La calibración es global por vuelo y no corrige las costuras internas del mosaico (se tratan con efectos espaciales).
   - Hay diferencias espectrales menores entre bandas S2 y RedEdge.
   - El desfase temporal es de hasta ±6 días.
   - La PSF de S2 se aproxima con una gaussiana.
   - Hay pocos sectores por campo (2-18 por vuelo; 442 en total).
7. **Resultados (55/55 vuelos con escena S2, |Δt| mediano 1 d):**
   - Ajuste agrupado: R² de 0,85-0,94 (azul), 0,85-0,89 (verde), 0,87-0,96 (rojo), 0,90-0,95 (red edge)
     y 0,80-0,96 (NIR); RMSE por vuelo de 0,004-0,017.
   - Desfases UAV-S2 hallados de 0-28 m (frecuentemente 10 m).
   - Validación física: el suelo y el NIR quedan en rangos razonables, pero el dosel puro queda con NDVI
     comprimido (0,56-0,78); ver `DATA_ISSUES.md`, IMG-07.
8. Si los autores entregan las capturas del panel, se calibra con panel y la calibración S2 queda como validación independiente.

### 2.3 Corregistro multitemporal → `06_coregistration.py`
- Correlación de fase de NIR entre cada fecha y una fecha de referencia por sitio-año. Meta: error < 1 GSD.
- Remuestreo a una grilla común por sitio-año (2 cm) para usar los mismos polígonos de parcela en todas las fechas.

### 2.4 Polígonos de parcela → `07_plot_grid.py`
- Entrada: matriz fila × columna del croquis + rotación (Description) + dimensiones (6,1 × 1,5 m; calles 0,75 m).
- Ajuste fino: perfiles de vegetación proyectados sobre los ejes rotados (los valles corresponden a las calles).
- Recorte de bordes para evitar efecto borde, como en Zhang 2021. Salida: GeoPackage por sitio-año con `plot_uid`.
  Validación visual con superposición sobre el CIR (figura del material suplementario).

### 2.5 Segmentación dosel / suelo / flor → `08_segmentation.py`
- Réplica: umbral de SAVI. Mejora: umbral automático (Otsu) y luego un clasificador píxel a píxel (RF o U-Net)
  entrenado con anotaciones mínimas, con una clase **flor** (flores blancas de arveja) que Zhang solo descartó.

---

## 3. Extracción de rasgos por parcela y fecha → `09_features.py`
- **Estructura:** cobertura del dosel (%), área y, si hay solape suficiente, altura con modelo digital de superficie
  (requiere las nubes o los DSM de Pix4D).
- **Índices de la réplica:** NDVI, GNDVI, SAVI, NDRE y TVI (media y suma).
- **Índices nuevos:** CIred-edge y CIgreen (clorofila), OSAVI, EVI2, MCARI, MTCI aproximado,
  razón RE/R y un índice de senescencia; percentiles (p10, p50, p90) y CV dentro de la parcela.
- **Textura:** GLCM (contraste, homogeneidad, energía y correlación) sobre NIR y NDVI.
- **Reproducción:** fracción de flor por parcela (arveja).
- **Tiempo:** días desde siembra y **grados-día acumulados** (base 3 °C).

## 4. Réplica de Zhang et al. (2021) → `10_replication.py`
- Correlaciones de Pearson parcela a parcela y por cultivar (media de 3 rep.) con rendimiento, días a floración y madurez.
- LASSO (α = 1, CV 5 × 3, rasgos seleccionados en ≥75 % de las corridas, partición 3:1 × 4 y LOO por cultivar),
  con normalización dentro de sitio-año.
- Tabla comparativa con sus valores reportados: r hasta 0,93 (garbanzo) y 0,85 (arveja), R² hasta 0,91 y 0,80.

## 5. Más allá de la réplica (aportes nuevos)
1. **Dinámica temporal:** curvas logísticas o P-splines de cobertura e índices contra grados-día por parcela.
   Parámetros: máximo, tasa, momento de inflexión, AUC, inicio y tasa de senescencia.
2. **Genética cuantitativa:** modelos mixtos (genotipo aleatorio, bloque y ambiente) para H² por fecha y por parámetro
   de curva. Correlaciones genéticas con el rendimiento, G×E multiambiente (factor-analítico o GGE),
   BLUPs y coincidencia de selección (solape del 20 % superior por rendimiento vs. por rasgo UAV).
3. **Fenología desde el aire:** fecha de 50 % de floración a partir de la fracción de flor y fecha de madurez a
   partir de la senescencia, validadas contra `fiftyflowr` y `physmatur` (Pullman).
4. **Morfología:** discriminación de tipo de hoja y tipo de semilla (verde/amarilla, kabuli) con firmas espectrales y temporales.

## 6. Machine Learning / Deep Learning → `11_models.py`
| Familia | Modelos | Entrada |
|---|---|---|
| Lineal regularizado (réplica) | LASSO, Elastic Net, PLSR | Rasgos por fecha |
| Árboles | Random Forest, XGBoost/LightGBM | Rasgos multifecha + parámetros de curva |
| Temporal | 1D-CNN, LSTM/GRU, Transformer ligero | Serie de índices interpolada en grados-día |
| Imagen | CNN (ResNet-18 de 5 canales), con preentrenamiento autosupervisado opcional sobre recortes sin etiqueta | Recortes de parcela multitemporales |

**Esquemas de validación**, del más optimista al más exigente:
1. CV aleatoria por parcela.
2. Dejar fuera el **genotipo** (todas sus repeticiones).
3. Dejar fuera el **sitio-año** (transferencia a un ambiente nuevo).
4. Temporal: entrenar con 2017-2018 y probar en 2019.

**Métricas:** R², RMSE, rRMSE, ρ de Spearman y coincidencia de selección top-k. También interpretabilidad (SHAP o
permutación) y costo computacional y huella de CO₂ (CodeCarbon), como en *Field to Pixel*.

## 7. Artículo
- Revistas objetivo: *Frontiers in Plant Science* (la misma de los trabajos replicados), *Plant Phenomics*
  o *Computers and Electronics in Agriculture*.
- Estructura: Introducción → Materiales y métodos (2.1-2.5 y 3-6) → Resultados (calidad de datos, réplica, temporal,
  genética, ML) → Discusión (qué se replica, qué no y por qué; transferibilidad) → Conclusiones.
- Disponibilidad: código en GitHub y rasgos por parcela en Zenodo (DOI). Las imágenes se publican solo con autorización de WSU/USDA-ARS.
- Figuras previstas:
  1. Sitios, diseño y calendario de vuelos.
  2. Flujo metodológico.
  3. Calibración (antes/después).
  4. Curvas temporales por panel.
  5. H² por fecha.
  6. Réplica vs. original.
  7. Desempeño de modelos por esquema de validación.
  8. Importancia de variables.
