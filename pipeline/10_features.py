"""Fase 3b - Rasgos por parcela y fecha a partir de reflectancia calibrada.

Para cada vuelo y cada parcela de su campo:
  1. Polígono de la grilla refinada (`07b`) desplazado por el corregistro del vuelo (`09`).
  2. Reflectancia por banda = offset + ganancia·DN (calibración Sentinel-2 por sectores, `05`).
  3. Máscara de dosel: SAVI (L = 0.5) > umbral de Otsu del vuelo-campo. Zhang et al. (2021) usaron umbrales de SAVI
     elegidos visualmente; Otsu es la versión automática y reproducible.
  4. Rasgos:
     - cobertura del dosel (fracción) y área de dosel (m²);
     - reflectancia media por banda en el dosel;
     - índices: NDVI, GNDVI, SAVI, NDRE, TVI (Zhang 2021) + OSAVI, EVI2, MCARI, CIgreen, CIrededge, MTCI;
       para cada uno: media en el dosel, media en la parcela, suma en el dosel (Zhang usa media y suma),
       p10/p50/p90 y CV;
     - textura GLCM del NIR (contraste, homogeneidad, energía, correlación; distancia 1; 0° y 90°).
  Los vuelos con bandas faltantes se incluyen; los índices que requieren esas bandas quedan NaN.
Salida: outputs/10_features/plot_date_features.csv.gz (una fila por parcela × vuelo)
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.features
from rasterio.windows import from_bounds
from skimage.feature import graycomatrix, graycoprops

sys.path.insert(0, str(Path(__file__).parent))
from config import BAND_ORDER, OUT, ROOT  # noqa: E402

OUTDIR = OUT / "10_features"
PAGE_FILTER = {1: dict(crop="pea"), 2: dict(crop="pea"), 3: dict(crop="chickpea"), 4: dict(crop="pea"),
               5: dict(crop="chickpea"), 6: {}, 7: dict(crop="pea"), 8: dict(crop="chickpea"), 9: dict(crop="pea"),
               10: dict(crop="chickpea"), 11: {}, 12: dict(stage="advanced")}


def otsu(x: np.ndarray) -> float:
    h, e = np.histogram(x, 256); m = (e[:-1] + e[1:]) / 2
    w0 = np.cumsum(h); w1 = w0[-1] - w0
    m0 = np.cumsum(h * m) / np.maximum(w0, 1); m1 = (np.sum(h * m) - np.cumsum(h * m)) / np.maximum(w1, 1)
    return float(m[np.argmax(w0 * w1 * (m0 - m1) ** 2)])


def indices(b: dict) -> dict:
    B, G, R, RE, N = (b.get(k) for k in ("blue", "green", "red", "red edge", "nir"))
    out = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        if N is not None and R is not None:
            out["NDVI"] = (N - R) / (N + R)
            out["SAVI"] = 1.5 * (N - R) / (N + R + 0.5)
            out["OSAVI"] = (N - R) / (N + R + 0.16)
            out["EVI2"] = 2.5 * (N - R) / (N + 2.4 * R + 1)
        if N is not None and G is not None:
            out["GNDVI"] = (N - G) / (N + G)
            out["CIgreen"] = N / G - 1
        if N is not None and RE is not None:
            out["NDRE"] = (N - RE) / (N + RE)
            out["CIrededge"] = N / RE - 1
        if N is not None and R is not None and G is not None:
            out["TVI"] = 0.5 * (120 * (N - G) - 200 * (R - G))
        if RE is not None and R is not None and G is not None:
            out["MCARI"] = ((RE - R) - 0.2 * (RE - G)) * (RE / R)
        if N is not None and RE is not None and R is not None:
            out["MTCI"] = (N - RE) / (RE - R)
    return out


def glcm_feats(nir: np.ndarray, mask: np.ndarray) -> dict:
    v = nir[mask]
    if v.size < 50:
        return {}
    lo, hi = np.percentile(v, [1, 99])
    q = np.clip((nir - lo) / (hi - lo + 1e-9) * 31, 0, 31).astype(np.uint8)
    q[~mask] = 0
    g = graycomatrix(q, [1], [0, np.pi / 2], levels=32, symmetric=True, normed=True)
    return {f"glcm_{p}": float(graycoprops(g, p).mean()) for p in ("contrast", "homogeneity", "energy", "correlation")}


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"]
    fl = pd.read_csv(OUT / "01_inventory" / "flight_inventory.csv")
    grid = gpd.read_file(OUT / "07_plot_grid" / "plot_grid_refined.gpkg", layer="plots")
    grid = grid[grid["kind"] == "plot"]
    co = pd.read_csv(OUT / "05_radiometric" / "calibration_coefficients.csv")
    cr = pd.read_csv(OUT / "09_coregistration" / "coregistration.csv")
    gdd = pd.read_csv(OUT / "08_weather" / "flight_gdd.csv")
    rows = []
    for page, g in grid.groupby("page"):
        sel = fl[(fl.year == g.year.iloc[0]) & (fl.site == g.site.iloc[0])]
        for k, v in PAGE_FILTER[int(page)].items():
            sel = sel[sel[k] == v]
        for f in sel.flight_dir:
            files = inv[inv.flight_dir == f].set_index("band")
            if files.empty:
                continue
            sh = cr[cr.flight_dir == f]
            # Vuelos con corregistro no resoluble se excluyen (riesgo de asignar la parcela vecina): docs/DATA_ISSUES.md
            if sh.empty or sh.iloc[0].status in ("AMBIGUO", "SIN_NIR_ROJO"):
                print(f"p{page} {f}: excluido (corregistro {sh.iloc[0].status if not sh.empty else 'ausente'})")
                continue
            dE, dN = (sh.iloc[0].shift_E_m, sh.iloc[0].shift_N_m) if not sh.empty else (0.0, 0.0)
            polys = g.copy()
            polys["geometry"] = polys.geometry.translate(dE, dN)
            cal = co[co.flight_dir == f].set_index("band")
            with rasterio.open(ROOT / files.iloc[0].path) as ref:
                crs, tr0 = ref.crs, ref.transform
            polys = polys.to_crs(crs)
            b = polys.total_bounds
            refl = {}
            for band in [x for x in BAND_ORDER if x in files.index]:
                with rasterio.open(ROOT / files.loc[band].path) as s:
                    win = from_bounds(*b, transform=s.transform).round_offsets().round_lengths()
                    d = s.read(window=win, boundless=True, fill_value=0)
                    wtr = s.window_transform(win)
                dn = d[0].astype(np.float32)
                valid = (d[-1] > 0) if d.shape[0] > 1 else dn > 0
                if band in cal.index:
                    r = cal.loc[band]
                    refl[band] = np.where(valid, r.offset + r.gain * dn, np.nan).astype(np.float32)
                else:  # banda sin coeficientes (p. ej. pocas muestras): se omite
                    continue
            if not refl:
                continue
            vi = indices(refl)
            labels = rasterio.features.rasterize([(geom, i + 1) for i, geom in enumerate(polys.geometry)],
                                                 out_shape=next(iter(refl.values())).shape, transform=wtr, fill=0,
                                                 dtype="int32")
            canopy_ref = vi.get("SAVI", vi.get("NDVI"))
            in_plots = labels > 0
            thr = otsu(canopy_ref[in_plots & np.isfinite(canopy_ref)]) if canopy_ref is not None else np.nan
            px_area = abs(wtr.a * wtr.e)
            date = sel[sel.flight_dir == f].date.iloc[0]
            for i, (_, p) in enumerate(polys.iterrows(), start=1):
                m = labels == i
                if m.sum() < 20:
                    continue
                rec = dict(plot_uid=p.plot_uid, page=page, year=p.year, site=p.site, trial=p.trial,
                           plot=int(p["plot"]), flight_dir=f, date=date, n_px=int(m.sum()),
                           valid_frac=float(np.isfinite(next(iter(refl.values()))[m]).mean()),
                           bands=",".join(refl), shift_E_m=dE, shift_N_m=dN, canopy_thr=thr)
                can = m & (canopy_ref > thr) if canopy_ref is not None else m
                rec["canopy_cover"] = float(can.sum() / m.sum())
                rec["canopy_area_m2"] = float(can.sum() * px_area)
                for band, a in refl.items():
                    rec[f"refl_{band.replace(' ', '')}"] = float(np.nanmean(a[can])) if can.any() else np.nan
                for name, a in vi.items():
                    vc, vp = a[can], a[m]
                    vc = vc[np.isfinite(vc)]; vp = vp[np.isfinite(vp)]
                    if vp.size == 0:
                        continue
                    rec[f"{name}_mean"] = float(vc.mean()) if vc.size else np.nan
                    rec[f"{name}_plotmean"] = float(vp.mean())
                    rec[f"{name}_sum"] = float(vc.sum() * px_area) if vc.size else 0.0
                    if vc.size:
                        p10, p50, p90 = np.percentile(vc, [10, 50, 90])
                        rec.update({f"{name}_p10": p10, f"{name}_p50": p50, f"{name}_p90": p90,
                                    f"{name}_cv": float(vc.std() / abs(vc.mean())) if vc.mean() else np.nan})
                if "nir" in refl:
                    ys, xs = np.where(m)
                    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
                    rec.update(glcm_feats(np.nan_to_num(refl["nir"][sl]), m[sl] & np.isfinite(refl["nir"][sl])))
                rows.append(rec)
            print(f"p{page} {f}: {len(polys)} parcelas, bandas={list(refl)}, umbral SAVI={thr:.3f}")
    df = pd.DataFrame(rows)
    g2 = gdd.rename(columns={"gdd_cum": "gdd"})[["flight_dir", "trial", "das", "gdd"]].drop_duplicates()
    df = df.merge(g2, on=["flight_dir", "trial"], how="left")
    df.to_csv(OUTDIR / "plot_date_features.csv.gz", index=False)
    print(df.groupby(["year", "site"]).agg(plots=("plot_uid", "nunique"), flights=("flight_dir", "nunique"),
                                           rows=("plot_uid", "size")).to_string())


if __name__ == "__main__":
    main()
