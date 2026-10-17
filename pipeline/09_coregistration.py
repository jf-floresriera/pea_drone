"""Fase 2.3 - Corregistro multitemporal: desfase de la grilla de parcelas en cada vuelo.

Primera versión (descartada): correlación de fase de bordes entre cada fecha y la referencia. Sobre un patrón
periódico de parcelas sufre aliasing (34/56 vuelos con desfases de 1-27 m, imposibles en mosaicos con GCP).
Intentos descartados (documentados): (i) correlación de fase de bordes y (ii) de NDVI suavizado entre fechas
(resultados inestables por el cambio fenológico y la periodicidad); (iii) emparejamiento de dianas GCP (las dianas
cambian de posición entre vuelos: 0-2 coincidencias).
Método adoptado: refinamiento de la grilla en cada vuelo, en los ejes de la grilla:
  - vegetación (NDVI con DN > Otsu del vuelo) a ≈5 cm;
  - traslación a lo largo de la parcela (eje ux, espaciamiento ≈6,1 m) en ±2,5 m y entre filas (eje uy, ≈2,0 m) en
    ±0,95 m (< medio espaciamiento: no puede saltar a la fila vecina), paso de 0,1 m y luego de 0,025 m;
  - objetivo: contraste de vegetación dentro de la parcela frente a la calle (muestreo por puntos de `07b`);
  - se acepta si el contraste final es > 0,10 y mejora en > 0,02; si no, desfase 0;
  - si el desfase entre filas queda a < 0,1 m del límite (±0,95 m), el vuelo se marca AMBIGUO (posible salto de fila).
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


def gcp_targets(flight: str, inv: pd.DataFrame, dec: int = 2) -> np.ndarray:
    """Centroides UTM de dianas GCP blancas (tableros) en el mosaico."""
    from scipy import ndimage as ndi
    arrs, tr, alpha = {}, None, None
    for b in ("blue", "green", "red", "nir"):
        r = inv[(inv.flight_dir == flight) & (inv.band == b)]
        if r.empty:
            continue
        with rasterio.open(ROOT / r.iloc[0].path) as s:
            d = s.read(out_shape=(s.count, s.height // dec, s.width // dec))
            tr = s.transform * s.transform.scale(s.width / d.shape[2], s.height / d.shape[1])
            res = abs(tr.a)
        arrs[b] = d[0].astype(np.float32) / 65520
        a = d[-1] > 0 if d.shape[0] > 1 else d[0] > 0
        alpha = a if alpha is None else alpha & a
    vis = [arrs[b] for b in ("blue", "green", "red") if b in arrs]
    if len(vis) < 2 or "nir" not in arrs or "red" not in arrs:
        return np.empty((0, 2))
    mn = np.minimum.reduce(vis)
    nd = (arrs["nir"] - arrs["red"]) / (arrs["nir"] + arrs["red"] + 1e-6)
    thr = np.percentile(mn[alpha], 99.97)
    m = alpha & (mn >= thr) & (np.abs(nd) < 0.15)
    lab, n = ndi.label(ndi.binary_opening(m))
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        reg = lab[sl] == i
        area = reg.sum() * res * res
        if 0.05 < area < 0.8 and reg.mean() > 0.5:
            cy, cx = ndi.center_of_mass(reg)
            x, y = tr * (sl[1].start + cx + 0.5, sl[0].start + cy + 0.5)
            out.append((x, y))
    return np.array(out)


def match_targets(ref: np.ndarray, mov: np.ndarray, max_t: float = 6.0, tol: float = 0.35):
    """Traslación ref→mov con más inliers entre todas las definidas por pares de dianas."""
    best = (0, None)
    if len(ref) < 3 or len(mov) < 3:
        return None, 0
    for a in ref:
        for b in mov:
            t = b - a
            if np.hypot(*t) > max_t:
                continue
            d = np.linalg.norm((ref + t)[:, None, :] - mov[None, :, :], axis=2)
            inl = (d.min(axis=1) < tol).sum()
            if inl > best[0] or (inl == best[0] and best[1] is not None and np.hypot(*t) < np.hypot(*best[1])):
                best = (inl, t)
    if best[0] < 3:
        return None, best[0]
    t = best[1]
    d = np.linalg.norm((ref + t)[:, None, :] - mov[None, :, :], axis=2)
    j = d.argmin(axis=1); ok = d.min(axis=1) < tol
    return (mov[j[ok]] - ref[ok]).mean(axis=0), int(ok.sum())


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
            to_EN = lambda aa, bb: aa * ux + bb * uy  # noqa: E731
            best = (c0, 0.0, 0.0)
            for aa in np.arange(-2.5, 2.501, 0.1):
                for bb in np.arange(-0.95, 0.951, 0.1):
                    t = to_EN(aa, bb); c = fs(np.array([t[0], t[1], 0, 1.0, 1.0]))
                    if c > best[0]:
                        best = (c, aa, bb)
            for aa in np.arange(best[1] - 0.1, best[1] + 0.101, 0.025):
                for bb in np.arange(max(-0.95, best[2] - 0.1), min(0.95, best[2] + 0.1) + 1e-6, 0.025):
                    t = to_EN(aa, bb); c = fs(np.array([t[0], t[1], 0, 1.0, 1.0]))
                    if c > best[0]:
                        best = (c, aa, bb)
            ok = best[0] > 0.10 and best[0] - c0 > 0.02
            aa, bb = (best[1], best[2]) if ok else (0.0, 0.0)
            sE, sN = to_EN(aa, bb)
            if f == rg.ref_flight:
                status = "REF"
            elif not ok:
                status = "SIN_MEJORA"
            elif abs(bb) > 0.85:
                status = "AMBIGUO"
            else:
                status = "AJUSTADO"
            rows.append(dict(page=rg.page, year=rg.year, site=rg.site, flight_dir=f, ref_flight=rg.ref_flight,
                             contrast_0=round(c0, 3), contrast=round(max(best[0], c0), 3), shift_along_m=round(aa, 3),
                             shift_across_m=round(bb, 3), shift_E_m=round(float(sE), 3), shift_N_m=round(float(sN), 3),
                             status=status))
            print(f"p{rg.page} {f}: contraste {c0:.2f} → {best[0]:.2f} · a lo largo {aa:+.2f} m, entre filas {bb:+.2f} m "
                  f"[{status}]", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUTDIR / "coregistration.csv", index=False)
    d = np.hypot(df.shift_E_m, df.shift_N_m)
    adj = df.status == "AJUSTADO"
    print(f"\n{len(df)} vuelos · estados {df.status.value_counts().to_dict()} · desfase mediano (ajustados) "
          f"{d[adj].median():.2f} m · máx {d.max():.2f} m · contraste mediano {df.contrast_0.median():.2f} → "
          f"{df.contrast.median():.2f}")


if __name__ == "__main__":
    main()
