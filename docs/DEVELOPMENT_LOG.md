# Bitácora de desarrollo

**Autor:** Jesús Enrique Flores Riera — candidato a Maestría en Geomática, Universidad Nacional de Colombia
(jfloresr@unal.edu.co).

Registro cronológico del desarrollo del proyecto: qué se ejecutó, qué falló, por qué y cómo se corrigió. Complementa:
- `docs/WORKFLOW.md`: la metodología;
- `docs/DATA_ISSUES.md`: los problemas de los datos y las decisiones tomadas;
- `docs/ROADMAP.md`: el estado y los pendientes.

Logs originales completos (sin editar) en [`docs/logs/`](logs/):

| Archivo | Contenido |
|---|---|
| `pipeline_run_2026-10-17.log` | Log en vivo del orquestador (`pipeline/run_pipeline.py`): 670 líneas, todas las ejecuciones del 17-oct |
| `pipeline_status_2026-10-17.json` | Estado final de los pasos según el orquestador |
| `paso_<NN>.log` | Salida completa de cada script (07b, 09-16, 15b), con la última ejecución de cada paso |

---

## 2026-10-16 — Fase 1: inventario, calidad y mapas de contexto
- **Inventario** de 275 ortomosaicos: 34 archivos vacíos (0 bytes), 44/55 vuelos con las 5 bandas completas.
- **Hallazgo:** los mosaicos están en DN (12 bit × 16) y no en reflectancia; los valores son físicamente imposibles
  como reflectancia (`DATA_ISSUES.md`, IMG-02).
- **QC de los Excel:** 2415 parcelas en 34 ensayos; 8 problemas registrados (unidades kg/ha, conteos, bloques, etc.).
- **Mapas de contexto:** se detectó que en Fairfield el garbanzo está en campos separados de la arveja (FLD-09).
- **Calibración radiométrica cruzada con Sentinel-2 L2A.**
  - La primera versión, píxel a píxel, dio R² de 0,0-0,6. Se rediseñó con **muestreo por sectores** de 20 m:
    PSF gaussiana, búsqueda de desfase y estratos.
  - Luego se seleccionó el modelo por **plausibilidad física**. Se descartó el de offset común por sesgo de
    atenuación y se adoptó el modelo por el origen (M3).

## 2026-10-17 — Fases 2-7: grilla, rasgos, análisis, modelos y figuras

### Grilla de parcelas (pasos 06, 07, 07b)
- **06.** Croquis del PDF digitalizados por el color vectorial de las celdas: 34/34 ensayos coinciden 1:1 con el Excel
  tras 4 correcciones explícitas (MAP-01). Se respetó el orden resaltado en verde por los autores (MAP-02).
- **07 (65 min).** Registro de la captura del croquis contra el mosaico por correlación de plantillas. La primera
  versión dio escalas erróneas y correlaciones espurias de 1,000. Se corrigió con:
  - máscara de datos válidos;
  - relleno de las zonas sin datos con ruido;
  - búsqueda de la relación de aspecto.
- **07b, ejecución 1 (10:59) — FALLÓ.** `TypeError` al dibujar la figura de Pullman 2019: el vuelo de referencia
  (17-jun) es parcial y no tiene banda verde.
  - *Corrección:* se usa el rojo como sustituto del verde en el compuesto de color.
  - Antes se había agregado un **prior físico**: en Pullman 2017 y Fairfield 2019 el registro tomaba las dos franjas
    de cada parcela como parcelas separadas (espaciamiento 1,0-1,3 m frente a ≈2,0 m), y se reescala al
    espaciamiento mediano (GRID-01).
- **07b, ejecución 2 (11:01) — OK, 2,0 min.** Contraste mediano de vegetación dentro/calle de 0,50; espaciamiento de
  6,07-6,29 × 1,87-2,06 m en los 12 campos.

### Corregistro multitemporal (paso 09)
- **09, versión 1 (11:04) — completó, pero con resultados inválidos.** La correlación de fase de bordes entre fechas
  dio 34/56 vuelos "sospechosos", con desfases de 1-27 m. Es aliasing por el patrón periódico de parcelas.
  - Se detuvo el pipeline antes de que el paso 10 usara esos desfases.
- **Intentos descartados:** emparejamiento de dianas GCP (0-2 coincidencias: cambian de posición entre vuelos) y
  correlación de NDVI suavizado (inestable por el cambio fenológico).
- **09, versión final (11:07) — OK, 0,9 min.** Refinamiento de la grilla en cada vuelo en los ejes de la grilla
  (±2,5 m a lo largo de la parcela y ±0,95 m entre filas). Desfase mediano de 0,7 m (máx. 2,1 m); contraste ≈0,1 → ≈0,4.
  4 vuelos ambiguos se excluyeron (GRID-03, GRID-04).

### Rasgos (paso 10)
- **Ejecución interrumpida (11:08)** a propósito, al cambiar el método de corregistro.
- **Ejecución final (11:17) — OK, 33,7 min.** 8079 registros parcela × vuelo, 2172 parcelas y 46 vuelos; se
  incluyeron vuelos con bandas parciales.

### Réplica de Zhang et al. 2021 (pasos 11, 11b)
- **11, ejecución 1 (11:51) — FALLÓ tras 65 min.** `ValueError: Found array with 0 feature(s)` en garbanzo 2019
  combinado. Pullman 2019 solo tiene vuelos tempranos y el filtro de completitud (70 %) eliminó todas las columnas de
  la grilla de grados-día.
  - *Correcciones:*
    - umbral de completitud al 50 % (imputación por mediana);
    - salida NaN si no queda ninguna variable;
    - checkpoint por resultado;
    - **paralelización** con joblib.
- **11, ejecución 2 (12:57) — OK, 33,0 min** (58 ajustes LASSO en paralelo).
- **11b (ejecución manual).** Sensibilidad de la normalización en los conjuntos combinados. Hallazgo clave: el R² alto
  publicado se reproduce solo con normalización sobre los sitios agrupados (garbanzo 2018: 0,28 frente a 0,82).

### Temporal, genética y fenología (pasos 12-14)
- **Pruebas previas en paralelo.** Se corrigieron:
  - la superposición de etiquetas en la figura de parámetros (leyenda común arriba);
  - la figura de H², que unía intervalos con muy pocos ensayos (ahora mediana e IQR, solo intervalos con ≥3 ensayos);
  - la evaluación de la fenología, que ahora usa la desviación respecto de la media del ambiente estimada con
    entrenamiento.
- **12 (1,4 min), 13 (1,3 min) y 14 (0,1 min) — OK.**

### Machine Learning (pasos 15, 15b)
- **15 (13:34) — los 8 bloques de evaluación terminaron (44 min), pero FALLÓ en la interpretabilidad (14:18).**
  `ValueError` en `shap.TreeExplainer`: el paquete `shap` 0.49 no lee el formato de `base_score` de XGBoost 3.x.
  - *Corrección:* SHAP exacto con la API nativa de XGBoost (`pred_contribs=True`) y modo `--post`, que rehízo la
    importancia y las figuras desde `results.csv` en 0,8 min, sin repetir el entrenamiento.
  - Por eso el log del orquestador no muestra "✓ PASO 15".
- **15b (ejecución manual).** Rasgos calibrados absolutos frente a estandarizados para predecir entre ambientes: la
  calibración reduce el RMSE en garbanzo (820 → 548-590 kg/ha), pero no en arveja.

### Figuras y tablas (paso 16)
- **16 (14:21) — OK.** 22 figuras y 5 tablas en `outputs/16_figures/`, más `RESULTS_SUMMARY.md`.
  - Se revisaron visualmente todas las figuras.
  - Se compactó la figura del flujo metodológico.
- Cada cifra del resumen de resultados se verificó contra las tablas de salida.

## 2026-10-19 — Autoría del repositorio
- Se quitaron las líneas de coautoría automática de los 25 commits (`git filter-branch`) y se publicó el historial
  corregido. Respaldo local: etiqueta `backup-antes-de-reescribir-2026-10-19`.
- Autor único: Jesús Enrique Flores Riera. La tarjeta "Contributors" de GitHub puede tardar en refrescar su caché;
  la API ya devuelve un único colaborador.

## 2026-10-20 — Documentación del desarrollo
- Se guardaron los logs completos en `docs/logs/` y se creó esta bitácora antes de reiniciar el equipo.

## 2026-10-28 — Organización del repositorio
- Nuevo README con la descripción de cada fase del trabajo, timelapse de vuelos y nota sobre el uso de IA.
- Las figuras y tablas finales quedan en `outputs/16_figures/` (se actualizó el paso 16).
- Se agregó `CITATION.cff` para citar el repositorio. Los logs originales de `docs/logs/` se conservan sin editar.

---

## Cómo retomar el trabajo después de reiniciar
```powershell
cd C:\Trabajo_eterno\drone_images
git pull                                   # traer la última versión
python pipeline\run_pipeline.py --from 16  # p. ej. regenerar figuras y tablas
Get-Content outputs\pipeline_run.log -Wait -Tail 40   # seguir el avance en vivo
```
Los ortomosaicos (`Images20NN/`) y los Excel no están en GitHub: deben estar en la raíz del proyecto en este equipo.
