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
  04_context_maps.py        mapas de localización, ensayos por campo y calendario de vuelos
  05_radiometric_calibration.py  calibración cruzada UAV→Sentinel-2 L2A por sectores
  06_parse_plot_maps.py     digitalización de los croquis (celdas, ensayo, fila/columna)
  07_georef_plot_grid.py    georreferenciación de la grilla (registro captura↔mosaico)
  07b_check_plot_grid.py    verificación y refinamiento afín de la grilla
docs/
  WORKFLOW.md            hoja de ruta metodológica completa (fases 0-7)
  ROADMAP.md             cola de trabajo: hecho / en curso / pendiente
  DATA_ISSUES.md         registro de problemas de datos y decisiones tomadas
  RADIOMETRIC_METHODS.md comparación de métodos de calibración radiométrica
  MODELING_PLAN.md       para qué y cómo se entrenan los modelos de ML/DL
  MANUSCRIPT.md          borrador vivo del artículo (inglés), con referencias verificadas
outputs/             resultados de cada paso (tablas, figuras, reportes)
```

## Reproducir
```bash
pip install -r requirements.txt
python pipeline/01_inventory_images.py
python pipeline/02_qc_tabular.py
python pipeline/03_spectral_histograms.py
python pipeline/04_context_maps.py   # requiere data_ext/ (Natural Earth + US Census, ver cabecera del script)
python pipeline/05_radiometric_calibration.py   # luego 06 y 07 (ver docs/WORKFLOW.md)
python pipeline/run_pipeline.py --from 07b   # resto en secuencia (07b → 16) con log y ETA
```
Los datos crudos (ortomosaicos `Images20NN/`, `20NNPulseDataset.xlsx`, `PulsePlotMaps_2017-2019.pdf`) no se versionan.
Se colocan en la raíz del repositorio con la misma estructura de carpetas.

## Estado
| Fase | Descripción | Estado |
|---|---|---|
| 1 | Inventario y QC (imágenes, campo, respuesta espectral) | ✅ |
| 1b | Mapas de contexto (localización, campos, calendario) | ✅ |
| 2 | Calibración radiométrica, croquis, grilla georreferenciada, corregistro | ✅ |
| 3-6 | Rasgos, réplica, temporal y genética, ML/DL | ✅ |
| 7 | Manuscrito (`docs/MANUSCRIPT.md`) + figuras y tablas (`outputs/16_manuscript/`) | ✅ borrador completo |

## Trabajo pendiente
Actualizado al 2026-10-19. El detalle completo está en [`docs/ROADMAP.md`](docs/ROADMAP.md).

**Decisiones del autor**
- [ ] Revisar el manuscrito completo (`docs/MANUSCRIPT.md`): redacción, título y énfasis de la discusión
- [ ] Definir la autoría final: director de tesis y, si corresponde, coautoría de los proveedores de los datos
      (S. Sankaran, R. J. McGee, G. J. Vandemark)
- [ ] Elegir la revista (propuesta: *Frontiers in Plant Science*)
- [ ] Versión en español del manuscrito, si la requiere la tesis de maestría

**Gestiones con los autores de los datos (WSU/USDA-ARS)**
- [ ] Autorización escrita para publicar los datos de campo (Excel y croquis de parcelas)
- [ ] Solicitar los 34 ortomosaicos vacíos (Pullman 2019 y red edge del garbanzo de Pullman 2017)
- [ ] Solicitar las imágenes crudas, las fotos del panel de reflectancia y los reportes de Pix4D

**Trabajo técnico antes del envío**
- [ ] Análisis de sensibilidad excluyendo los campos con grilla de confianza media
      (Pullman 2017 arveja y Genesee 2018; `docs/DATA_ISSUES.md`, GRID-02)
- [ ] Formato de la revista:
  - plantilla y límite de palabras;
  - figuras en TIFF a 300-600 dpi;
  - declaraciones de contribución, financiación y conflicto de interés
- [ ] Depósito del código y las tablas derivadas en Zenodo (DOI) y actualización de *Data availability*

**Extensiones opcionales (no bloquean el artículo)**
- [ ] Modelos espaciales con P-splines (SpATS, R) y heredabilidad de Cullis
- [ ] Detección de flores de arveja a alta resolución para la fenología
- [ ] CNN sobre recortes de imagen por parcela

## Autor
**Jesús Enrique Flores Riera** — candidato a Maestría en Geomática, Universidad Nacional de Colombia
(jfloresr@unal.edu.co). Autor único del análisis, el código y la documentación de este repositorio.

## Créditos de datos
Los ensayos y las imágenes no son del autor: pertenecen a R. J. McGee y G. J. Vandemark (USDA-ARS Grain Legume
Genetics and Physiology Research Unit) y a S. Sankaran y C. Zhang (WSU Biological Systems Engineering). Se usan con
autorización, citando el artículo original:

> Zhang, C., McGee, R. J., Vandemark, G. J., & Sankaran, S. (2021). Crop performance evaluation of chickpea and dry pea
> breeding lines across seasons and locations using phenomics data. *Frontiers in Plant Science*, 12, 640259.
> https://doi.org/10.3389/fpls.2021.640259

## Mantenimiento del repositorio
**Autoría de los commits.** Todos los commits figuran a nombre de Jesús Enrique Flores Riera
<jfloresr@unal.edu.co>, sin líneas de coautoría. Configuración local usada:
```bash
git config user.name  "Jesús Enrique Flores Riera"
git config user.email "jfloresr@unal.edu.co"
```

**Historial reescrito (2026-10-19).** Las líneas `Co-Authored-By` de los commits anteriores se quitaron con
`git filter-branch`. El contenido de los archivos no cambió: solo cambiaron los mensajes y los autores. El historial
previo queda respaldado en la etiqueta local `backup-antes-de-reescribir-2026-10-19`. Para publicarlo en GitHub
(reemplaza el historial remoto; hacerlo una sola vez):
```bash
git diff backup-antes-de-reescribir-2026-10-19 main --stat   # debe salir vacío (mismo contenido)
git push --force-with-lease origin main
```
Si algo sale mal, se recupera con `git reset --hard backup-antes-de-reescribir-2026-10-19`.
