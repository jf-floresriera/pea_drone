# Multi-season UAV multispectral phenotyping of dry pea and chickpea breeding trials: a reproducible re-analysis with satellite-anchored radiometric calibration, temporal canopy dynamics and cross-environment machine learning

**Working draft — living document.** Sections marked **[PENDING]** depend on analyses in the queue (`docs/ROADMAP.md`).
All numbers reported here come from the scripts in `pipeline/` and the tables in `outputs/`. All references were
checked against bibliographic records before inclusion.

**Authors:** J. E. Flores-Riera (Universidad Nacional de Colombia) — *co-authors and order to be agreed*.
**Data:** UAV imagery and field data from Washington State University (S. Sankaran) and USDA-ARS Grain Legume
Genetics and Physiology Research Unit (R. J. McGee, G. J. Vandemark), originally analysed by Zhang et al. (2021).

---

## Abstract [PENDING final results]
**Background.** Unmanned aerial vehicle (UAV) multispectral imaging has been proposed to replace labour-intensive
field evaluations in pulse breeding. Zhang et al. (2021) showed that canopy area and vegetation indices from a five-band
camera correlated with seed yield and phenology of chickpea (*Cicer arietinum* L.) and dry pea (*Pisum sativum* L.)
advanced yield trials across three seasons and three locations of the Palouse region (USA). However, their models were
fitted within each site-year after normalisation, so it is still unknown whether these relationships transfer
across environments.
**Methods.** We re-analysed the same dataset from the original orthomosaics: 55 flights × 5 bands, 2017–2019, Pullman (WA),
Fairfield (WA) and Genesee (ID), 34 trials and 2,415 plots. We built a fully reproducible open-source workflow covering:
- data-quality auditing;
- radiometric calibration of uncalibrated orthomosaics by sector-based cross-calibration against Sentinel-2 L2A surface
  reflectance;
- automatic georeferencing of plot layouts by registering the field maps to the orthomosaics;
- extraction of calibrated spectral, textural and temporal (growing-degree-day based) traits;
- replication of the original correlation and LASSO analyses;
- extensions with spatially corrected mixed models (heritability, genetic correlations, G×E) and machine-learning models
  validated across genotypes, environments and years.
**Results.** [PENDING]
**Conclusions.** [PENDING]

**Keywords:** high-throughput phenotyping; UAV; multispectral; radiometric calibration; Sentinel-2; pulse breeding;
*Pisum sativum*; *Cicer arietinum*; heritability; machine learning; reproducibility.

---

## 1. Introduction
**Phenotyping bottleneck.** Field phenotyping is widely recognised as the main bottleneck limiting the use of
genomic and breeding advances, and proximal and remote sensing platforms have been proposed to relieve it
(Araus and Cairns, 2014). Low-altitude UAV imaging gives centimetre-level resolution over whole trials in minutes.
It has been reviewed for emergence, vigour, stress and yield-potential assessment in row and field crops (Sankaran et al., 2015).

**Pulse crops.** In cool-season pulses, UAV-derived indices and canopy metrics have been related to above-ground biomass
and performance traits in pea (Quirós Vargas et al., 2019). Zhang et al. (2021) extended this to multi-season,
multi-location advanced yield trials of chickpea and dry pea:
- Canopy area, NDVI, SAVI and NDRE features correlated with seed yield (r up to 0.93 at cultivar level) and with days to
  flowering and maturity.
- LASSO models predicted yield with test R² up to 0.91 when data were pooled within a year.

Marzougui et al. (2023) later combined UAV and satellite data for field-pea yield estimation with random forests
under entry-level hold-out. Fusing features across platforms and time points gave R² up to 0.72.

**Open problems.** Three issues limit the use of these results in breeding programmes:
1. **Radiometric consistency.** Multispectral UAV data must be converted to surface reflectance before indices can be
   compared across dates, sites and years. Standard workflows rely on reflectance panels and irradiance sensors
   (Aasen et al., 2018).
   - When only processed orthomosaics are archived, the panel information is lost.
   - Image-based alternatives such as the empirical line method (Smith and Milton, 1999) and pseudo-invariant
     normalisation (Canty and Nielsen, 2008) need in-scene references.
   - Open satellite surface-reflectance products such as Sentinel-2 L2A (Drusch et al., 2012; Main-Knorn et al., 2017)
     offer an external radiometric reference, but the scale mismatch (centimetres vs. 10–20 m) must be handled explicitly.
2. **Temporal information.** Most analyses treat each flight separately. Time-series modelling of canopy development,
   for example sigmoid growth curves fitted to UAV canopy cover and height, can produce interpretable dynamic traits such
   as maximum growth rate, early vigour and senescence (Borra-Serrano et al., 2020).
3. **Genetic and statistical rigour.** Breeding decisions rely on genotype means corrected for field heterogeneity.
   - Spatial mixed models with P-splines (Rodríguez-Álvarez et al., 2018) and heritability definitions suited to
     unbalanced trials (Cullis et al., 2006; Piepho and Möhring, 2007; Holland et al., 2003) are needed to judge whether
     a UAV trait is useful for selection.
   - Predictive models must be validated on genotypes and environments not seen during training.

**Objectives.** Using the dataset of Zhang et al. (2021) re-processed from the orthomosaics, we aimed to:
1. audit and document the dataset and build a reproducible open workflow;
2. derive radiometrically consistent reflectance through satellite-anchored cross-calibration;
3. replicate the original correlation and LASSO analyses;
4. extend them with temporal canopy-dynamics traits, spatially corrected genetic parameters and machine-learning models
   validated across genotypes, environments and years.

---

## 2. Materials and Methods

### 2.1 Field trials
The trials were advanced and preliminary yield trials of the USDA-ARS pulse breeding programme, grown in 2017–2019 at
Pullman (WA), Fairfield (WA) and Genesee (ID). The Genesee 2017 trial was lost (Zhang et al., 2021).
- **Design:** randomised complete blocks with three replicates. Plots were 6.1 m × 1.5 m; chickpea plots were trimmed
  after emergence (Zhang et al., 2021).
- **Market classes (Table 1):**

| Crop | Market class | Plots | Entries |
|---|---|---|---|
| Pea | Green pea | 1,017 | 113 |
| Pea | Yellow pea | 549 | 68 |
| Pea | Green-yellow pea (New Zealand) | 210 | 33 |
| Chickpea | Kabuli chickpea | 615 | 86 |
| Chickpea | Green chickpea | 24 | 8 |

- **Totals:** 2,415 plots and 303 distinct entries (210 pea, 93 chickpea).
- **Seed yield:** recorded for all trials. Trial means ranged from 675 to 3,600 kg ha⁻¹ and within-trial CV from 9.0 to 46.8 %.
- **Other traits:** days to 50 % flowering, days to physiological maturity, vine length, canopy height, pod height and
  related architecture traits, recorded at Pullman (and reported for Fairfield 2017).

**Table 1.** Plots and entries by crop and market class (`outputs/02_tabular_qc/`).

### 2.2 UAV data
- **Platform and sensor:** AgBot quadcopter (ATI) with a MicaSense RedEdge camera (blue 475, green 560, red 668,
  red-edge 717, NIR 840 nm).
- **Flights:** 3–7 dates per site-year between early June and mid-August, flown at 25–45 m above ground.
- **Archived product:** per-band Pix4D orthomosaics (`transparent_mosaic`) in UTM zone 11N, with ground sampling
  distance from 1.4 to 3.3 cm (median 1.8 cm).
- **Inventory:** 55 flights (275 band files). 34 files were empty (0 bytes), so 44 flights have all five bands
  (Supplementary Fig. S2; `outputs/01_inventory/`).
- **Data gaps:**
  - Pullman 2019 has only one complete date.
  - Chickpea at Pullman 2017 lacks the red-edge band on five dates.

### 2.3 Data-quality audit
Field spreadsheets were consolidated into a plot-level table and checked automatically (`pipeline/02_qc_tabular.py`) for:
- plot, entry and replicate counts against the trial descriptions;
- duplicates and missing values;
- unit consistency;
- date coherence and outliers;
- entry-mean repeatability of seed yield.

Every issue and the decision taken are logged (`docs/DATA_ISSUES.md`). Two examples:
- Seed yield is labelled g ha⁻¹ but is in kg ha⁻¹.
- At Fairfield the chickpea trials were planted in fields 2–6 km away from the pea trials, although the trial
  descriptions give a single coordinate per site.

Physiological and phenological records were used as delivered by the original investigators.

### 2.4 Radiometric calibration
**Diagnosis.**
- The orthomosaics store 12-bit digital numbers scaled to 16 bits (maximum 65,520), not reflectance.
- Values are physically implausible as reflectance. For dense canopy, the blue median was 0.27–0.32 of full scale and the
  NIR/red ratio 2.9–3.6; bare soil gave negative NDVI.
- No reflectance panel was visible in any mosaic. The only bright targets were ground-control-point boards, which were
  saturated in 2018–2019.

**Sector-based cross-calibration with Sentinel-2 L2A** (`pipeline/05_radiometric_calibration.py`):
1. **Scene selection.** For each flight we selected the closest Sentinel-2 L2A scene (|Δt| ≤ 6 days) with ≥ 95 % of the
   flight footprint classified as vegetation or bare soil by the scene classification layer. Scenes were accessed through
   the Microsoft Planetary Computer STAC API.
2. **Band pairing.** RedEdge bands were paired with MSI bands B02, B03, B04, B05 (20 m) and B08.
3. **Why sectors.** A direct pixel-wise comparison is degraded by three effects: Sentinel-2 geolocation error, the
   MSI point-spread function, and mixing of plots and alleys at 10 m. Initial pixel-wise per-flight fits gave R² ≤ 0.6,
   with negative values for NIR.
4. **Sector procedure.**
   - UAV digital numbers were aggregated to 2 m.
   - They were convolved with a Gaussian approximation of the Sentinel-2 PSF (σ = 4 m for 10 m bands, 8 m for B05).
   - They were averaged over 20 m sectors aligned with the Sentinel-2 grid.
   - The UAV–Sentinel-2 offset was searched within ±20 m by maximising the joint NIR/red correlation.
   - Only homogeneous sectors were kept: full UAV coverage, clear-sky classification in the whole sector, and within-sector
     NIR coefficient of variation ≤ 0.25.
   - Sectors were stratified by Sentinel-2 NDVI into soil, mixed and canopy strata.
5. **Calibration model.** Two candidate models were fitted on the sectors with robust (Huber) or ordinary least squares:
   - **M2:** ρ_S2 = b(year, band) + g(flight, band) · DN, with an offset shared by all flights of a season.
   - **M3:** ρ_S2 = g(flight, band) · DN, least squares through the origin.
   Because the within-field reflectance range is narrow and digital numbers are noisy, M2 slopes suffer from attenuation
   (errors-in-variables) bias. Its high pooled R² mainly reflects between-flight level differences, while within-flight
   contrast is flattened. The model was therefore selected by **physical plausibility**: a penalty measuring departure of
   calibrated canopy and soil medians from expected ranges (canopy NDVI ≥ 0.85, soil NDVI 0.05–0.25, canopy red ≤ 0.08),
   rather than by R².

### 2.5 Plot-layout digitisation and georeferencing
The authors' field maps (13 pages) are vector tables overlaid on screenshots of the rotated orthomosaics.
- **Digitisation.** Cells were extracted with their vector fill colours; the colour identifies the trial through the
  coloured side labels. Rows and columns were obtained by clustering cell coordinates (`pipeline/06_parse_plot_maps.py`).
- **Corrections.** Four documented typing errors were corrected. A row whose order the authors had highlighted as a
  planting change was kept as drawn.
- **Georeferencing** (`pipeline/07_georef_plot_grid.py`):
  1. The embedded screenshot was registered to the red-band orthomosaic by normalised cross-correlation, searching rotation
     (around the plot-rotation angle in the trial description and its mirrored and 180° alternatives), scale and aspect
     ratio, coarse-to-fine.
  2. Correlations were evaluated only where ≥ 97 % of the template overlapped valid data.
  3. The composed transformation maps every cell to UTM coordinates.
- **Plot polygons.** Centred on each cell and oriented along the grid axes, with 80 % of the inter-column and 70 % of the
  inter-row spacing to exclude borders and alleys.
- **Refinement** (`pipeline/07b_check_plot_grid.py`). An affine refinement (translation, rotation and anisotropic scale)
  maximised the contrast between vegetation fraction inside the polygons and in a 0.4–0.5 m surrounding ring
  (vegetation = digital-number NDVI above the flight's Otsu threshold).
  - In two fields the registration locked onto the two canopy strips visible within each plot (row spacing 1.0–1.3 m
    instead of ≈2.0 m). Because all trials share the same plot design (6.1 m × 1.5 m plus alleys), spacings departing
    > 20 % from the median of the other fields were rescaled to that median before refinement.
- **Multi-temporal co-registration** (`pipeline/09_coregistration.py`). Orthomosaics of different dates were offset from
  each other by a median of 0.68 m (maximum 2.1 m), despite the use of ground control points.
  - Image-to-image phase correlation, smoothed-NDVI correlation and matching of ground-control targets all failed:
    respectively because of aliasing on the periodic plot pattern, phenological change between dates, and targets
    moved between flights.
  - The grid was therefore re-fitted to every flight by translation only, along the grid axes: ±2.5 m along the plot
    and ±0.95 m across rows, i.e. less than half the row spacing, so a shift to the neighbouring row is impossible.
  - Flights whose across-row shift reached the search limit (4 of 52) were excluded as ambiguous.

### 2.6 Trait extraction
For each plot and date, calibrated reflectance is summarised after soil and flower masking:
- canopy cover;
- the indices used by Zhang et al. (2021): NDVI (Rouse et al., 1974), GNDVI (Gitelson et al., 1996), SAVI (Huete, 1988),
  NDRE (Barnes et al., 2000) and TVI (Broge and Leblanc, 2001);
- additional indices: OSAVI (Rondeaux et al., 1996), EVI2 (Jiang et al., 2008), MCARI (Daughtry et al., 2000) and the
  green and red-edge chlorophyll indices (Gitelson et al., 2003);
- within-plot percentiles;
- GLCM texture (Haralick et al., 1973).

- **Canopy mask.** Calibrated SAVI above the Otsu (1979) threshold of each flight and field, an automatic analogue of
  the visually chosen SAVI thresholds of Zhang et al. (2021). Each index was summarised as canopy mean, plot mean,
  canopy sum, percentiles and coefficient of variation (`pipeline/10_features.py`).
- **Thermal time.** Growing degree days from sowing with a 3 °C base, as in Zhang et al. (2021), computed from Daymet V4
  daily weather (Thornton et al., 2022) at the centroid of each field (`pipeline/08_weather_gdd.py`).
- **Common thermal-time grid.** Because each site-year was flown on different dates, plot traits were linearly
  interpolated to 400, 550, 700, 850, 1000 and 1150 °C·d for pooled analyses, without extrapolation.

### 2.7 Replication analysis
Pearson correlations between traits and seed yield, days to flowering and days to maturity are computed at plot and
cultivar level. LASSO yield models are fitted with the original settings: α = 1, 5-fold × 3 cross-validation, features
retained in ≥ 75 % of runs, 3:1 split repeated four times and leave-one-cultivar-out (Tibshirani, 1996; Zhang et al., 2021).
- **Leakage-free variant.** In the original procedure, feature selection uses the full dataset before splitting. We
  therefore also report a "nested" variant in which selection is repeated within every training partition.
- **Sensitivity of pooled datasets.** For data pooled within a year we compared standardisation within site against
  standardisation over the pooled dataset (`pipeline/11b_replication_sensitivity.py`).

### 2.8 Temporal, genetic and phenological analyses
- **Growth curves.** Logistic and P-spline curves are fitted per plot to canopy cover and indices against growing degree
  days. Parameters: maximum, maximum rate, inflection, area under the curve and senescence rate (cf. Borra-Serrano et al., 2020).
- **Mixed models.** Spatial mixed models (SpATS; Rodríguez-Álvarez et al., 2018) provide genotype BLUEs/BLUPs and
  generalised heritability (Cullis et al., 2006; Piepho and Möhring, 2007).
  - The model was fitted by REML (statsmodels) with block and quadratic row/column trends as fixed effects.
  - Entry-mean heritability was computed as σ²g/(σ²g + σ²e/r).
- **Downstream analyses.**
  - Correlations between genotypic values (μ + BLUP) of UAV traits and of seed yield. These approximate genetic
    correlations and are biased towards zero by shrinkage.
  - Coincidence of the top 20 % genotypes selected by yield and by each UAV trait.
  - G×E for trials repeated across sites: crossed genotype and genotype × environment variance components.
- **Phenology.** Days to flowering and to maturity were predicted with ridge regression on curve parameters and
  thermal-time-grid traits under genotype-grouped 5-fold cross-validation. Targets were deviations from the
  environment mean, estimated on training plots only (`pipeline/14_phenology.py`).

### 2.9 Machine learning
- **Models:** LASSO, elastic net, PLSR, random forests (Breiman, 2001), XGBoost (Chen and Guestrin, 2016), temporal
  convolutional/recurrent networks, and CNNs on multi-temporal plot image chips.
- **Validation schemes:** random-plot, leave-genotype-out, leave-environment-out and forward-in-time.
- **Interpretation:** SHAP values (Lundberg and Lee, 2017) and permutation importance (`docs/MODELING_PLAN.md`).

### 2.10 Software and reproducibility
- Analyses run in Python 3.10 (rasterio, GeoPandas, scikit-learn, OpenCV, PyMuPDF, pystac-client) with versions pinned
  in `requirements.txt`.
- Each step is a numbered script whose outputs are versioned.
- Code: https://github.com/jf-floresriera/pea_drone

---

## 3. Results (partial)

### 3.1 Dataset audit
- **Completeness.** 241 of 275 band files were readable; 44 of 55 flights have all five bands.
- **Repeatability.** Entry-mean repeatability of seed yield ranged from 0.17 to 0.94 among trials (median 0.72).
  Trials with low repeatability are expected to limit any trait–yield association.
- **Logged issues.** Eight field-data and seven image issues; the full list is in `docs/DATA_ISSUES.md`.

### 3.2 Radiometric calibration
- **Coverage.** All 55 flights were matched to a clear Sentinel-2 L2A scene (median |Δt| = 1 day, maximum 6).
- **Sectors.** 442 valid 20 m sectors were obtained (2–18 per flight).
- **Geolocation offsets.** Non-zero UAV–Sentinel-2 offsets (10–28 m) were found in 64 % of flights, which confirms that
  geolocation mismatch is a major error source in direct pixel comparisons.
- **Model comparison.** M2 reached pooled R² of 0.80–0.96 but had near-zero (some negative) gains in the blue, green
  and red-edge bands. M3 had pooled R² of 0.59–0.95 (green 2017 was not fitted) with median per-flight RMSE of
  0.004–0.018 reflectance units. Physical-plausibility penalty: 0.46 (M2) vs. 0.29 (M3); M3 was adopted (Table 2).
- **Physical plausibility (M3).** Soil values were plausible (median NDVI 0.27, red 0.14). The vegetation class remained
  compressed (median NDVI 0.59, red 0.076).
- **Interpretation.** The archived orthomosaics are not linear in radiance, most likely because of colour balancing
  during mosaicking. The calibration harmonises scale across dates, sites and years at plot and field level, but absolute
  reflectance of pure canopy pixels should be interpreted with caution.

**Table 2.** Pooled R² of the adopted through-origin calibration (M3) by band and year
(`outputs/05_radiometric/calibration_coefficients.csv`).

| Year | Blue | Green | Red | Red edge | NIR |
|---|---|---|---|---|---|
| 2017 | 0.589 | −0.068 | 0.740 | 0.762 | 0.615 |
| 2018 | 0.806 | 0.755 | 0.898 | 0.882 | 0.800 |
| 2019 | 0.864 | 0.702 | 0.951 | 0.784 | 0.949 |

### 3.3 Plot-layout digitisation, georeferencing and co-registration
- **Digitisation.** After four documented corrections, the digitised maps matched the field records exactly for all 34
  trials (2,415 plots).
- **Georeferencing.** The refined grids reproduced the physical plot spacing in all 12 georeferenced fields
  (6.07–6.29 m along plots, 1.87–2.06 m across rows). The median inside/alley vegetation contrast was 0.50
  (range 0.08–0.67).
  - The two lowest values belong to reference flights with senescent pea (Pullman 2017, 28 July; contrast 0.08) or with
    canopy closed over the alleys (Genesee 2018, 6 August; 0.16). Both were checked visually and flagged as
    medium-confidence fields.
- **Co-registration.** It raised the median contrast of non-reference flights from 0.08 to 0.40. Shifts had a median
  of 0.68 m (maximum 2.09 m), mostly along the plot axis.
- **Final dataset.** 8,079 plot × flight records from 2,172 plots and 46 flights. The preliminary 2019 Pullman trials
  have no usable imagery.

### 3.4 Replication of Zhang et al. (2021)
**Correlations.** The single-flight correlations were of the same magnitude as published (Table 3; Supplementary Fig. S4).
- Seed yield, plot level: maximum |r| of 0.77 for kabuli chickpea (canopy area, Genesee 2019; published 0.74) and 0.79
  for green pea (GNDVI sum, Fairfield 2017; published up to 0.83).
- Seed yield, cultivar level: maximum r of 0.88 for chickpea (published 0.93).
- Phenology: correlations reached 0.65 (yellow pea, NDRE) at plot level and 0.76–0.86 at cultivar level, for days to
  flowering and maturity respectively, close to the published 0.76–0.85.

**LASSO yield models.** These replicated only partly (Table 3; Fig. 7).
- For 2019 chickpea the test R² was comparable or higher: Genesee 0.69 vs. 0.51; Pullman 0.50 vs. 0.57.
- For 2017–2018 and Fairfield 2019 it was markedly lower, and pooled within-year models reached R² 0.17–0.28
  (published 0.82–0.89).
- Removing information leakage (nested selection) lowered R² in most datasets, by up to ≈ 0.25.
- **The gap in pooled models is explained by normalisation** (Supplementary Fig. S9). When features and yield were
  standardised over the pooled dataset rather than within site, pooled-model R² rose to values close to the published
  ones:

  | Pooled dataset | Within-site standardisation | Pooled standardisation | Published |
  |---|---|---|---|
  | Chickpea 2018 | 0.28 | 0.82 | 0.89 |
  | Chickpea 2019 | 0.17 | 0.60 | 0.82 |
  | Green pea 2018 | 0.27 | 0.72 | up to 0.80 |
  | Green pea 2019 | 0.25 | 0.75 | up to 0.80 |

  Under pooled standardisation the between-site differences in yield remain in the target and are easily predicted from
  site-level differences in canopy vigour. The high pooled R² therefore mostly reflects environment discrimination
  rather than genotype discrimination within a trial.

### 3.5 Canopy dynamics in thermal time
- **Curve fits.** Logistic curves fitted the growth phase of 72–76 % of plots, depending on the trait, with median
  R² 0.91–0.94 for canopy cover and NDVI (Fig. 5).
- **Inflection.** Canopy cover reached its inflection at a median of 446–480 °C·d in green pea, yellow pea and kabuli
  chickpea, and later in green chickpea (530 °C·d), i.e. before the reported flowering window (721–772 °C·d).
- **Senescence.** Fastest in yellow pea (median −0.15 per 100 °C·d) and slowest in kabuli chickpea (−0.06).

### 3.6 Genetic parameters of UAV traits
**Heritability (Table 4; Fig. 6).**
- Field traits: entry-mean heritability was high, as expected for advanced trials (seed yield 0.80–0.92 across market
  classes; days to flowering 0.87–0.99).
- Single-flight UAV traits: median H² was 0.77 for canopy cover, 0.83 for NDVI, 0.80 for GNDVI and 0.72 for NDRE.
- Integrated dynamic traits were also heritable: canopy-cover AUC 0.81–0.93; NDVI AUC 0.53–0.79. The inflection time
  of canopy cover was not (median ≈ 0).

**Correlations with seed yield at genotype level** differed sharply between crops.
- **Chickpea:** median correlations of 0.66 (canopy cover and area) and 0.69 (NDRE).
- **Pea:** ≤ 0.18 despite comparable heritability, consistent with the difficulty reported for pea canopies with
  tendrils and stipules (Zhang et al., 2021).
- **Coincidence of the top 20 %:** median 0.33–0.41 for canopy traits.

**G×E for seed yield.** In trials repeated across sites in 2018–2019, the G×E variance was 0.37–1.02 times the genotypic
variance, and multi-environment heritability was 0.56–0.77.

### 3.7 Phenology from UAV time series
- **Correlations.** The strongest correlates were NDRE AUC and maximum. With days to flowering in pea: r = 0.49 and 0.44.
  With days to maturity in pea: 0.47; in chickpea, NDVI AUC gave −0.48.
- **Genotype-grouped prediction.** Prediction of within-environment deviations was weak: R² 0.02–0.16 (r = 0.16–0.40).
  RMSE was 3.2 days for flowering and 3.9–5.5 days for maturity.
- **Interpretation.** Within a given trial, UAV dynamics rank flowering and maturity moderately well. Predicting them
  for unseen genotypes with a pooled model does not yet replace field scoring.

### 3.8 Machine-learning models [PENDING]

## 4. Discussion (outline) [PENDING]
1. **Archived orthomosaics as a reusable resource.** What can and cannot be recovered without raw imagery and panel data.
   Satellite anchoring as a pragmatic solution, and its limits: non-linearity, PSF approximation and temporal mismatch.
2. **Replication outcome.** Agreement and disagreement with Zhang et al. (2021), and the effect of radiometric harmonisation.
3. **Temporal traits and heritability.** Which traits are heritable and genetically correlated with yield, and at which
   thermal time.
4. **Transferability.** Performance across genotypes, environments and years versus within-environment results, and
   implications for operational selection.
5. **Limitations.**
   - Missing 2019 Pullman imagery.
   - Phenology recorded only at Pullman.
   - Small number of environments.
   - The archived products were not radiometric products.

---

## Data availability
Code and derived tables: https://github.com/jf-floresriera/pea_drone. Field data and imagery belong to WSU/USDA-ARS and
are used with permission; users must cite Zhang et al. (2021). [Repository/DOI for derived plot-level data: PENDING
authors' agreement.]

## References
*(Checked against bibliographic records — journal, volume, pages and DOI.)*

- Aasen, H., Honkavaara, E., Lucieer, A., Zarco-Tejada, P. J. (2018). Quantitative remote sensing at ultra-high resolution with UAV spectroscopy: a review of sensor technology, measurement procedures, and data correction workflows. *Remote Sensing* 10(7), 1091. https://doi.org/10.3390/rs10071091
- Araus, J. L., Cairns, J. E. (2014). Field high-throughput phenotyping: the new crop breeding frontier. *Trends in Plant Science* 19(1), 52–61.
- Barnes, E. M., et al. (2000). Coincident detection of crop water stress, nitrogen status and canopy density using ground-based multispectral data. *Proceedings of the 5th International Conference on Precision Agriculture*, Bloomington, MN, USA.
- Borra-Serrano, I., et al. (2020). Closing the phenotyping gap: high resolution UAV time series for soybean growth analysis provides objective data from field trials. *Remote Sensing* 12(10), 1644. https://doi.org/10.3390/rs12101644
- Breiman, L. (2001). Random forests. *Machine Learning* 45, 5–32.
- Broge, N. H., Leblanc, E. (2001). Comparing prediction power and stability of broadband and hyperspectral vegetation indices for estimation of green leaf area index and canopy chlorophyll density. *Remote Sensing of Environment* 76, 156–172.
- Canty, M. J., Nielsen, A. A. (2008). Automatic radiometric normalization of multitemporal satellite imagery with the iteratively re-weighted MAD transformation. *Remote Sensing of Environment* 112(3), 1025–1036. https://doi.org/10.1016/j.rse.2007.07.013
- Chen, T., Guestrin, C. (2016). XGBoost: a scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD*, 785–794.
- Cullis, B. R., Smith, A. B., Coombes, N. E. (2006). On the design of early generation variety trials with correlated data. *Journal of Agricultural, Biological, and Environmental Statistics* 11(4), 381–393. https://doi.org/10.1198/108571106X154443
- Daughtry, C. S. T., et al. (2000). Estimating corn leaf chlorophyll concentration from leaf and canopy reflectance. *Remote Sensing of Environment* 74, 229–239.
- Drusch, M., et al. (2012). Sentinel-2: ESA's optical high-resolution mission for GMES operational services. *Remote Sensing of Environment* 120, 25–36. https://doi.org/10.1016/j.rse.2011.11.026
- Gitelson, A. A., Kaufman, Y. J., Merzlyak, M. N. (1996). Use of a green channel in remote sensing of global vegetation from EOS-MODIS. *Remote Sensing of Environment* 58, 289–298.
- Gitelson, A. A., Gritz, Y., Merzlyak, M. N. (2003). Relationships between leaf chlorophyll content and spectral reflectance and algorithms for non-destructive chlorophyll assessment in higher plant leaves. *Journal of Plant Physiology* 160, 271–282.
- Haralick, R. M., Shanmugam, K., Dinstein, I. (1973). Textural features for image classification. *IEEE Transactions on Systems, Man, and Cybernetics* SMC-3(6), 610–621.
- Holland, J. B., Nyquist, W. E., Cervantes-Martínez, C. T. (2003). Estimating and interpreting heritability for plant breeding: an update. *Plant Breeding Reviews* 22, 9ff. *(volume dated 2002 by the publisher; verify year and pages at citation)*
- Huete, A. R. (1988). A soil-adjusted vegetation index (SAVI). *Remote Sensing of Environment* 25, 295–309.
- Jiang, Z., Huete, A. R., Didan, K., Miura, T. (2008). Development of a two-band enhanced vegetation index without a blue band. *Remote Sensing of Environment* 112, 3833–3845.
- Lundberg, S. M., Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems* 30.
- Main-Knorn, M., Pflug, B., Louis, J., Debaecker, V., Müller-Wilm, U., Gascon, F. (2017). Sen2Cor for Sentinel-2. *Proc. SPIE* 10427, 1042704. https://doi.org/10.1117/12.2278218
- Marzougui, A., McGee, R. J., Van Vleet, S., Sankaran, S. (2023). Remote sensing for field pea yield estimation: a study of multi-scale data fusion approaches in phenomics. *Frontiers in Plant Science* 14, 1111575. https://doi.org/10.3389/fpls.2023.1111575
- Otsu, N. (1979). A threshold selection method from gray-level histograms. *IEEE Transactions on Systems, Man, and Cybernetics* 9(1), 62–66.
- Piepho, H.-P., Möhring, J. (2007). Computing heritability and selection response from unbalanced plant breeding trials. *Genetics* 177, 1881–1888.
- Quirós Vargas, J. J., Zhang, C., Smitchger, J. A., McGee, R. J., Sankaran, S. (2019). Phenotyping of plant biomass and performance traits using remote sensing techniques in pea (*Pisum sativum*, L.). *Sensors* 19(9), 2031. https://doi.org/10.3390/s19092031
- Rodríguez-Álvarez, M. X., Boer, M. P., van Eeuwijk, F. A., Eilers, P. H. C. (2018). Correcting for spatial heterogeneity in plant breeding experiments with P-splines. *Spatial Statistics* 23, 52–71. https://doi.org/10.1016/j.spasta.2017.10.003
- Rondeaux, G., Steven, M., Baret, F. (1996). Optimization of soil-adjusted vegetation indices. *Remote Sensing of Environment* 55, 95–107.
- Rouse, J. W., Haas, R. H., Schell, J. A., Deering, D. W. (1974). Monitoring vegetation systems in the Great Plains with ERTS. *Third ERTS Symposium*, NASA SP-351, 309–317.
- Sankaran, S., et al. (2015). Low-altitude, high-resolution aerial imaging systems for row and field crop phenotyping: a review. *European Journal of Agronomy* 70, 112–123. https://doi.org/10.1016/j.eja.2015.07.004
- Smith, G. M., Milton, E. J. (1999). The use of the empirical line method to calibrate remotely sensed data to reflectance. *International Journal of Remote Sensing* 20, 2653–2662.
- Thornton, M. M., Shrestha, R., Wei, Y., Thornton, P. E., Kao, S.-C., Wilson, B. E. (2022). Daymet: daily surface weather data on a 1-km grid for North America, Version 4 R1. ORNL DAAC. https://doi.org/10.3334/ORNLDAAC/2129
- Tibshirani, R. (1996). Regression shrinkage and selection via the lasso. *Journal of the Royal Statistical Society: Series B* 58(1), 267–288.
- Zhang, C., McGee, R. J., Vandemark, G. J., Sankaran, S. (2021). Crop performance evaluation of chickpea and dry pea breeding lines across seasons and locations using phenomics data. *Frontiers in Plant Science* 12, 640259. https://doi.org/10.3389/fpls.2021.640259
