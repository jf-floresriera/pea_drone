# Métodos de calibración radiométrica: opciones evaluadas

**Situación de partida.** Ortomosaicos Pix4D `transparent_mosaic` en DN (12 bit × 16). No hay imágenes crudas, ni capturas
del panel, ni metadatos del sensor de irradiancia (DLS). En los mosaicos solo aparecen dianas GCP, cuyos blancos están saturados.

| # | Método | Qué requiere | ¿Aplicable hoy? | Ventajas | Limitaciones |
|---|---|---|---|---|---|
| 1 | **Panel + línea empírica sobre imágenes crudas** (flujo MicaSense: DN → radiancia con ganancia, exposición y viñeteo → reflectancia con el panel) | TIFF crudos de cada captura y fotos del panel antes y después del vuelo | ❌ (pedir a WSU) | Estándar de referencia; el que usaron Zhang et al. (2021) | Hay que rehacer el mosaico en Pix4D/Metashape/ODM |
| 2 | **Panel + DLS** (corrección por irradiancia incidente por foto) | Crudos con metadatos DLS | ❌ | Corrige cambios de luz durante el vuelo, causa de las **costuras** | El DLS es ruidoso con nubes parciales |
| 3 | **Calibración cruzada con Sentinel-2 L2A** ← *adoptado* | Mosaicos + S2 L2A abierto (±6 días, sin nubes) | ✅ | Reflectancia absoluta y consistente entre fechas, sitios y años; reproducible; bandas casi idénticas | Píxel de 10-20 m (≈100 píxeles por campo); Δt de días; no corrige costuras internas |
| 4 | Calibración cruzada con **PlanetScope** (3 m, casi diaria) | Acceso a Planet (programa Education & Research) | ⚠️ con cuenta | 10× más píxeles por campo y Δt ≈ 0-1 día | Radiometría menos estable que S2; sin red edge en Dove-R 2017-2019 (solo SuperDove desde 2020) |
| 5 | **Normalización relativa con objetos pseudo-invariantes** (IR-MAD / PIF: caminos, grava, techos) | Mosaicos corregistrados entre fechas | ✅ | No depende de satélite; ideal para la **serie temporal dentro de un sitio-año** | Solo relativa: necesita una fecha absoluta (p. ej. del método 3); pocos invariantes en campos agrícolas |
| 6 | Línea empírica con objetos del terreno de reflectancia conocida (asfalto, lonas negras de las GCP) | Espectros medidos en campo | ❌ | Simple | No hay espectros de campo y los blancos están saturados |
| 7 | Solo índices normalizados + estandarización por vuelo (z-score dentro de sitio-fecha) | Nada | ✅ | Es lo que de hecho hacen Zhang et al. al normalizar dentro de año y sitio; suficiente para correlaciones dentro de ambiente | No sirve para comparar fechas ni ambientes, ni para curvas temporales ni ML entre ambientes |
| 8 | Corrección de costuras / no uniformidad dentro del mosaico (ajuste radiométrico por bloques; tendencia espacial) | Mosaicos (o crudos) | ✅ parcial | Reduce gradientes del campo | Riesgo de quitar señal genética real; se prefiere modelarla con efectos fila/columna (SpATS) |

## Decisión
1. **Absoluta (entre fechas, sitios y años): método 3**, Sentinel-2 L2A. Coeficientes por banda y vuelo en
   `outputs/05_radiometric/calibration_coefficients.csv`.
2. **Control de consistencia temporal: método 5** (PIF/IR-MAD) dentro de cada sitio-año, como validación cruzada del 3.
3. **Variación espacial dentro del vuelo: método 8**, como efecto espacial en los modelos mixtos, no como corrección de imagen.
4. **Análisis de réplica (dentro de ambiente): se reporta también el método 7**, para comparar en igualdad de condiciones
   con Zhang et al. (2021).
5. Si los autores entregan crudos y panel, se aplica el método 1 a un subconjunto y se valida el método 3 contra él.

## Lecturas recomendadas
- MicaSense. *RedEdge radiometric calibration model* e *imageprocessing* (GitHub micasense/imageprocessing).
- Smith & Milton (1999). The use of the empirical line method to calibrate remotely sensed data to reflectance. *IJRS* 20:2653.
- Canty & Nielsen (2008). Automatic radiometric normalization of multitemporal satellite imagery with the iteratively
  re-weighted MAD transformation. *RSE* 112:1025.
- Aasen et al. (2018). Quantitative remote sensing at ultra-high resolution with UAV spectroscopy: a review of sensor
  technology, measurement procedures, and data correction workflows. *Remote Sens.* 10:1091.
- Mamaghani & Salvaggio (2019). Multispectral sensor calibration and characterization for sUAS remote sensing. *Sensors* 19:4453.
- Pendiente: revisión bibliográfica de estudios de consistencia UAV vs. Sentinel-2 (búsqueda "UAV Sentinel-2 radiometric
  cross-calibration"), Verificar las referencias antes de citarlas.
- Rodríguez-Álvarez et al. (2018). Correcting for spatial heterogeneity in plant breeding experiments with P-splines (SpATS). *Spatial Statistics* 23:52.
