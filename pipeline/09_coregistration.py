"""Fase 2.3 - Corregistro multitemporal: desfase de la grilla de parcelas en cada vuelo.

Primera versión (descartada): correlación de fase de bordes entre cada fecha y la referencia. Sobre un patrón
periódico de parcelas sufre aliasing (34/56 vuelos con desfases de 1-27 m, imposibles en mosaicos con GCP).
Método adoptado (grilla como referencia, sin aliasing):
  1. Para cada vuelo se calcula la vegetación (NDVI con DN > umbral de Otsu del vuelo) a ≈5 cm.
  2. Se busca la traslación de la grilla refinada (`07b`) que maximiza el contraste de vegetación dentro de las
     parcelas frente a un anillo exterior (calles), en ±0,9 m (menos de medio espaciamiento entre filas ≈2 m, de modo
     que no puede saltar a la parcela vecina), paso de 0,1 m y refinamiento de 0,025 m.
  3. Se acepta si mejora el contraste en > 0,02 y el contraste final es > 0,10; si no (p. ej. vuelos tempranos con poco
     dosel), se usa desfase 0, lo esperable en mosaicos con GCP.
Salida: outputs/09_coregistration/coregistration.csv (shift_E_m, shift_N_m a sumar a la grilla en cada vuelo)
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT, ROOT  # noqa: E402

_spec = importlib.util.spec_from_file_location("chk", Path(__file__).parent / "07b_check_plot_grid.py")
chk = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(chk)
OUTDIR = OUT / "09_coregistration"
DEC = 3
PAGES = {1: dict(crop="pea"), 2: dict(crop="pea"), 3: dict(crop="chickpea"), 4: dict(crop="pea"),
         5: dict(crop="chickpea"), 6: {}, 7: dict(crop="pea"), 8: dict(crop="chickpea"), 9: dict(crop="pea"),
         10: dict(crop="chickpea"), 11: {}, 12: dict(stage="advanced")}


def veg_map(flight: str, inv: pd.DataFrame):
    def rd(b):
        r = inv[(inv.flight_dir == flight) & (inv.band == b)]
        if r.empty:
            return None, None, None
        with rasterio.open(ROOT / r.iloc[0].path) as s:
            a = s.read(1, out_shape=(s.height // DEC, s.width // DEC)).astype(np.float32)
            tr = s.transform * s.transform.scale(s.width / a.shape[1], s.height / a.shape[0])
            return np.where(a > 0, a, np.nan), tr, s.crs
    nir, tr, crs = rd("nir"); red, _, _ = rd("red")
    if nir is None or red is None:
        return None, None, None
    nd = (nir - red) / (nir + red)
    v = (nd > chk.otsu(nd[np.isfinite(nd)])).astype(np.float32)
    v[~np.isfinite(nd)] = np.nan
    return v, tr, crs


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"]
    fl = pd.read_csv(OUT / "01_inventory" / "flight_inventory.csv")
    reg = pd.read_csv(OUT / "07_plot_grid" / "registration.csv")
    grid = gpd.read_file(OUT / "07_plot_grid" / "plot_grid_refined.gpkg", layer="plots")
    rows = []
    for _, rg in reg[reg.status == "OK"].iterrows():
        sel = fl[(fl.year == rg.year) & (fl.site == rg.site)]
        for k, v in PAGES[int(rg.page)].items():
            sel = sel[sel[k] == v]
        g = grid[(grid.page == rg.page) & (grid["kind"] == "plot")]
        for f in sel.flight_dir:
            veg, tr, crs = veg_map(f, inv)
            if veg is None:
                rows.append(dict(page=rg.page, year=rg.year, site=rg.site, flight_dir=f, shift_E_m=0.0, shift_N_m=0.0,
                                 status="SIN_NIR_ROJO"))
                continue
            gl = g.to_crs(crs)
            C = np.column_stack([gl.E, gl.N]) if crs.to_epsg() == 32611 else \
                np.column_stack([gl.geometry.centroid.x, gl.geometry.centroid.y])
            ux = np.array([gl.ux_E.iloc[0], gl.ux_N.iloc[0]]); uy = np.array([gl.uy_E.iloc[0], gl.uy_N.iloc[0]])
            hx, hy = 0.80 * gl.pitch_col_m.iloc[0] / 2, 0.70 * gl.pitch_row_m.iloc[0] / 2
            fs = chk.make_sampler(veg, tr, C, C.mean(axis=0), ux, uy, hx, hy)
            c0 = fs(np.array([0, 0, 0, 1.0, 1.0]))
            best = (c0, 0.0, 0.0)
            for dE in np.arange(-0.9, 0.91, 0.1):
                for dN in np.arange(-0.9, 0.91, 0.1):
                    c = fs(np.array([dE, dN, 0, 1.0, 1.0]))
                    if c > best[0]:
                        best = (c, dE, dN)
            for dE in np.arange(best[1] - 0.1, best[1] + 0.101, 0.025):
                for dN in np.arange(best[2] - 0.1, best[2] + 0.101, 0.025):
                    c = fs(np.array([dE, dN, 0, 1.0, 1.0]))
                    if c > best[0]:
                        best = (c, dE, dN)
            ok = best[0] - c0 > 0.02 and best[0] > 0.10
            sE, sN = (best[1], best[2]) if ok else (0.0, 0.0)
            status = "REF" if f == rg.ref_flight else ("AJUSTADO" if ok else "SIN_MEJORA")
            rows.append(dict(page=rg.page, year=rg.year, site=rg.site, flight_dir=f, ref_flight=rg.ref_flight,
                             contrast_0=round(c0, 3), contrast=round(max(best[0], c0), 3), shift_E_m=round(sE, 3),
                             shift_N_m=round(sN, 3), status=status))
            print(f"p{rg.page} {f}: contraste {c0:.2f} → {best[0]:.2f}  desfase ({sE:+.2f}, {sN:+.2f}) m [{status}]",
                  flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUTDIR / "coregistration.csv", index=False)
    d = np.hypot(df.shift_E_m, df.shift_N_m)
    print(f"\n{len(df)} vuelos · ajustados {int((df.status == 'AJUSTADO').sum())} · desfase mediano (ajustados) "
          f"{d[df.status == 'AJUSTADO'].median():.2f} m · máx {d.max():.2f} m")


if __name__ == "__main__":
    main()
