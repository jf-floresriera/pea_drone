"""Carga y preparación de datos compartida por los análisis (pasos 11-16).

- `load()`: rasgos por parcela × vuelo (`10`) + datos de campo (`02`) + clase comercial, genotipo y bloque.
- `REPL_FEATURES`: rasgos de la réplica de Zhang et al. (2021): área de dosel y media/suma de NDVI, GNDVI, SAVI, NDRE, TVI.
- `gdd_grid()`: interpola cada rasgo de cada parcela a una grilla común de grados-día (los sitio-año se volaron en
  fechas distintas), sin extrapolar fuera del rango observado.
- `zscore_within()`: estandarización dentro de ambiente (sitio-año), como en Zhang et al. (2021).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT  # noqa: E402

VIS_REPL = ["NDVI", "GNDVI", "SAVI", "NDRE", "TVI"]
VIS_NEW = ["OSAVI", "EVI2", "MCARI", "CIgreen", "CIrededge", "MTCI"]
REPL_FEATURES = ["canopy_area_m2"] + [f"{v}_{s}" for v in VIS_REPL for s in ("mean", "sum")]
CORE_FEATURES = (["canopy_cover", "canopy_area_m2"] + [f"{v}_mean" for v in VIS_REPL + VIS_NEW]
                 + [f"{v}_sum" for v in VIS_REPL] + ["NDVI_cv", "NDRE_cv", "glcm_contrast", "glcm_homogeneity"])
TRAITS = ["seedyield", "fiftyflowr", "physmatur", "canopyht", "vinelength", "podht"]
GDD_GRID = np.array([400, 550, 700, 850, 1000, 1150])


def load() -> pd.DataFrame:
    f = pd.read_csv(OUT / "10_features" / "plot_date_features.csv.gz", dtype={"trial": str})
    p = pd.read_csv(OUT / "02_tabular_qc" / "plots_master.csv", dtype={"trial": str})
    keep = ["plot_uid", "crop", "market_class", "trial_stage", "entry", "entry_name", "block"] + \
           [t for t in TRAITS if t in p]
    d = f.merge(p[keep], on="plot_uid", how="inner")
    d["env"] = d.year.astype(str) + "_" + d.site
    d["date"] = pd.to_datetime(d.date)
    return d


def wide_by_flight(d: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """Una fila por parcela; columnas rasgo@fecha (orden por GDD del vuelo)."""
    d = d.copy()
    d["tag"] = d.groupby("env").gdd.rank(method="dense").astype(int).astype(str).radd("t")
    w = d.pivot_table(index="plot_uid", columns="tag", values=feats)
    w.columns = [f"{a}@{b}" for a, b in w.columns]
    return w


def gdd_grid(d: pd.DataFrame, feats: list[str], grid=GDD_GRID) -> pd.DataFrame:
    """Interpolación lineal por parcela de cada rasgo a la grilla de GDD (NaN fuera del rango observado)."""
    rows = {}
    for uid, g in d.sort_values("gdd").groupby("plot_uid"):
        x = g.gdd.to_numpy()
        rec = {}
        for f in feats:
            if f not in g:
                continue
            y = g[f].to_numpy(dtype=float)
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < 2:
                continue
            xi = np.interp(grid, x[ok], y[ok], left=np.nan, right=np.nan)
            for gg, v in zip(grid, xi):
                rec[f"{f}@{gg}"] = v
        rows[uid] = rec
    return pd.DataFrame.from_dict(rows, orient="index")


def plot_table(d: pd.DataFrame) -> pd.DataFrame:
    cols = ["plot_uid", "env", "year", "site", "trial", "crop", "market_class", "trial_stage", "entry", "entry_name",
            "block"] + [t for t in TRAITS if t in d]
    return d[cols].drop_duplicates("plot_uid").set_index("plot_uid")


def zscore_within(s: pd.Series, groups: pd.Series) -> pd.Series:
    return s.groupby(groups).transform(lambda v: (v - v.mean()) / v.std(ddof=0) if v.std(ddof=0) > 0 else v * 0)
