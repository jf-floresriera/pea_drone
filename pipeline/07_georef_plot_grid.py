"""Fase 2.4b - Georreferenciación de la grilla de parcelas a partir de los croquis.

Cada página del PDF de croquis tiene incrustada una captura del ortomosaico (rotado y recortado al ensayo) bajo la
tabla de celdas. Registrando esa captura contra el ortomosaico real, cada celda (número de parcela) se convierte en
una coordenada UTM:

  celda (pt PDF) → píxel de la captura → mosaico rotado/escalado → mosaico submuestreado → mosaico completo → UTM

Registro (por página):
  1. Mosaico: banda roja (dosel oscuro, suelo claro, como la captura) submuestreada ×8 y normalizada.
  2. Búsqueda gruesa por correlación normalizada (cv2.matchTemplate) con plantilla de 160 px: ángulos
     {±θ, ±θ+180} ± 3° (θ = "Plot Rotation" de Description) y 14 escalas; en todas las fechas del campo.
  3. Refinamiento de los 3 mejores ángulos base con plantilla de 500 px, pasos de 0.25° y ±10 % de escala.
  4. Se elige el máximo; las superposiciones (tablero de ajedrez) quedan en outputs/07_plot_grid/registration/.
Polígonos: rectángulo centrado en la celda, orientado según los ejes de la grilla; largo y ancho = 80 % y 70 % del
espaciamiento medido entre centros vecinos (recorte de bordes y calles, como en Zhang et al. 2021).
Salidas: outputs/07_plot_grid/{plot_grid.gpkg, plot_centers.csv, registration.csv, registration/*.png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import geopandas as gpd
import numpy as np
import pandas as pd
import pymupdf
import rasterio
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT, PLOT_MAPS_PDF, ROOT  # noqa: E402

OUTDIR = OUT / "07_plot_grid"
K = 8                      # submuestreo del mosaico para el registro
TW_COARSE, TW_FINE = 160, 500
LEN_FRAC, WID_FRAC = 0.80, 0.70
PAGES = {  # página → (año, sitio, filtro de vuelos por columnas de flight_inventory)
    1: (2017, "Fairfield", dict(crop="pea")), 2: (2017, "Pullman", dict(crop="pea")),
    3: (2017, "Pullman", dict(crop="chickpea")), 4: (2018, "Fairfield", dict(crop="pea")),
    5: (2018, "Fairfield", dict(crop="chickpea")), 6: (2018, "Genesee", {}),
    7: (2018, "Pullman", dict(crop="pea")), 8: (2018, "Pullman", dict(crop="chickpea")),
    9: (2019, "Fairfield", dict(crop="pea")), 10: (2019, "Fairfield", dict(crop="chickpea")),
    11: (2019, "Genesee", {}), 12: (2019, "Pullman", dict(stage="advanced")),
    13: (2019, "Pullman", dict(stage="preliminary")),
}


def norm(x: np.ndarray) -> np.ndarray:
    x = np.nan_to_num(x, nan=float(np.nanmean(x)))
    return ((x - x.mean()) / (x.std() + 1e-6)).astype(np.float32)


def load_red(flight_dir: str, inv: pd.DataFrame):
    r = inv[(inv.flight_dir == flight_dir) & (inv.band == "red") & (inv.status == "OK")]
    if r.empty:
        return None
    with rasterio.open(ROOT / r.iloc[0].path) as src:
        a = src.read(1, out_shape=(src.height // K, src.width // K)).astype(np.float32)
        tr = src.transform * src.transform.scale(src.width / a.shape[1], src.height / a.shape[0])
        crs = src.crs
    v = a > 0
    lo, hi = np.percentile(a[v], [1, 99])
    m = np.clip((a - lo) / (hi - lo), 0, 1)
    m[~v] = np.nan
    return m, tr, crs


def rotation(shape, ang):
    h, w = shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    c, s = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * s + w * c), int(h * c + w * s)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    return np.vstack([M, [0, 0, 1]]), (nw, nh)


_RNG = np.random.default_rng(0)


def rotated_scaled(m, ang, sc, tw):
    """Mosaico rotado `ang` y escalado para que una captura de ancho tw ocupe la fracción `sc` del ancho rotado.
    Las zonas sin datos se rellenan con ruido (evita correlaciones espurias de 1.0 en áreas constantes)."""
    M, (nw, nh) = rotation(m.shape, ang)
    R = cv2.warpAffine(np.nan_to_num(m, nan=-1), M[:2], (nw, nh), borderValue=-1)
    valid = (R >= 0).astype(np.float32)
    k = tw / (sc * nw)
    rs = (max(1, int(nw * k)), max(1, int(nh * k)))
    Rn = norm(np.where(valid > 0, R, np.nan))
    Rn = np.where(valid > 0, Rn, _RNG.standard_normal(Rn.shape).astype(np.float32))
    return cv2.resize(Rn, rs, interpolation=cv2.INTER_AREA), cv2.resize(valid, rs, interpolation=cv2.INTER_AREA)


def match(m, bg, ang, sc, tw, aspect=1.0, cache=None):
    """cc máximo de la captura (ancho tw, alto × aspect) dentro del mosaico rotado/escalado, exigiendo ≥97 % de
    datos válidos bajo la plantilla."""
    key = (round(ang, 3), round(sc, 4), tw)
    if cache is not None and key in cache:
        Rs, V = cache[key]
    else:
        Rs, V = rotated_scaled(m, ang, sc, tw)
        if cache is not None:
            cache[key] = (Rs, V)
    th = int(bg.shape[0] * tw / bg.shape[1] * aspect)
    if Rs.shape[1] <= tw or Rs.shape[0] <= th:
        return -1.0, None
    T = norm(cv2.resize(bg, (tw, th), interpolation=cv2.INTER_AREA))
    cc = cv2.matchTemplate(Rs, T, cv2.TM_CCOEFF_NORMED)
    vf = cv2.matchTemplate(V, np.ones_like(T), cv2.TM_CCORR) / T.size
    cc[vf < 0.97] = -1
    _, mx, _, loc = cv2.minMaxLoc(cc)
    return float(mx), loc


def bg_to_mosaic_px(ang, sc, loc, tw, bg_shape, m_shape, aspect=1.0):
    """Matriz 3×3: píxel de la captura → píxel del mosaico submuestreado."""
    M, (nw, _) = rotation(m_shape, ang)
    k = tw / (sc * nw)
    s_bg = tw / bg_shape[1]
    A = np.array([[s_bg, 0, loc[0]], [0, s_bg * aspect, loc[1]], [0, 0, 1]])  # captura → mosaico rotado escalado
    S = np.diag([1 / k, 1 / k, 1])                                             # → mosaico rotado
    return np.linalg.inv(M) @ S @ A                                            # → mosaico submuestreado


def register(bg, flights, inv, rot0):
    cands = []
    data = {f: load_red(f, inv) for f in flights}
    data = {f: d for f, d in data.items() if d is not None}
    for f, (m, _, _) in data.items():
        cache = {}
        for base in (rot0, -rot0, rot0 + 180, -rot0 + 180):
            for da in np.arange(-3, 3.01, 1.0):
                for sc in np.geomspace(0.25, 1.2, 14):
                    for asp in (0.8, 1.0, 1.25):
                        cc, _ = match(m, bg, base + da, sc, TW_COARSE, asp, cache)
                        cands.append((cc, f, base + da, sc, asp))
    cands.sort(key=lambda c: -c[0])
    seen, top = set(), []
    for c in cands:  # 3 mejores combinaciones (vuelo, ángulo redondeado a 10°) distintas
        key = (c[1], round(c[2] / 10))
        if key not in seen:
            seen.add(key); top.append(c)
        if len(top) == 3:
            break
    best = (-1,)
    for _, f, ang0, sc0, asp0 in top:
        m, cache = data[f][0], {}
        for ang in np.arange(ang0 - 1.5, ang0 + 1.51, 0.25):
            for sc in sc0 * np.geomspace(0.9, 1.1, 9):
                for asp in asp0 * np.geomspace(0.85, 1.15, 9):
                    cc, loc = match(m, bg, ang, sc, TW_FINE, asp, cache)
                    if cc > best[0]:
                        best = (cc, f, ang, sc, loc, asp)
        cache.clear()
    return best, data


def overlay_png(bg, m, ang, sc, loc, path, title, aspect=1.0):
    Rs, _ = rotated_scaled(m, ang, sc, TW_FINE)
    bgf = cv2.resize(bg, (TW_FINE, int(bg.shape[0] * TW_FINE / bg.shape[1] * aspect)),
                     interpolation=cv2.INTER_AREA)
    crop = Rs[loc[1]:loc[1] + bgf.shape[0], loc[0]:loc[0] + bgf.shape[1]]
    to01 = lambda a: np.clip((a - np.percentile(a, 2)) / (np.percentile(a, 98) - np.percentile(a, 2) + 1e-6), 0, 1)
    bgf, crop = to01(bgf), to01(crop)
    cb = crop.copy(); h, w = crop.shape; n = 8
    for i in range(n):
        for j in range(n):
            if (i + j) % 2 == 0:
                cb[i * h // n:(i + 1) * h // n, j * w // n:(j + 1) * w // n] = bgf[i * h // n:(i + 1) * h // n,
                                                                                   j * w // n:(j + 1) * w // n]
    pan = (np.hstack([bgf, crop, cb]) * 255).astype(np.uint8)
    cv2.putText(pan, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 255, 2)
    cv2.imwrite(str(path), pan)


def main() -> None:
    (OUTDIR / "registration").mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    fl = pd.read_csv(OUT / "01_inventory" / "flight_inventory.csv")
    cells = pd.read_csv(OUT / "06_plot_maps" / "plot_map_cells.csv", dtype={"trial": str})
    desc = pd.read_csv(OUT / "02_tabular_qc" / "trials_description.csv", dtype={"trial": str})
    doc = pymupdf.open(PLOT_MAPS_PDF)
    regs, centers = [], []
    for pno, (year, site, filt) in PAGES.items():
        sel = fl[(fl.year == year) & (fl.site == site)]
        for k_, v in filt.items():
            sel = sel[sel[k_] == v]
        flights = [f for f in sel.flight_dir if
                   not inv[(inv.flight_dir == f) & (inv.band == "red") & (inv.status == "OK")].empty]
        if not flights:
            regs.append(dict(page=pno, year=year, site=site, status="SIN_IMAGENES"))
            print(f"pág {pno}: sin mosaicos con banda roja → no se georreferencia")
            continue
        page = doc[pno - 1]
        xref = page.get_images(full=True)[0][0]
        rect = page.get_image_rects(xref)[0]
        pix = pymupdf.Pixmap(doc, xref)
        if pix.colorspace is None or pix.colorspace.n != 1:
            pix = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.Pixmap(pymupdf.csRGB, pix))
        bg = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).astype(np.float32)
        trials_pg = cells[cells.page == pno].trial.dropna().unique()
        rot0 = float(desc[(desc.year == year) & (desc.site == site) & desc.trial.isin(trials_pg)]
                     .plot_rotation_deg.iloc[0])
        (cc, f, ang, sc, loc, asp), data = register(bg, flights, inv, rot0)
        m, tr, crs = data[f]
        overlay_png(bg, m, ang, sc, loc, OUTDIR / "registration" / f"p{pno:02d}_{year}_{site}.png",
                    f"p{pno} {f} ang={ang:.2f} sc={sc:.3f} asp={asp:.3f} cc={cc:.3f}", asp)
        H = bg_to_mosaic_px(ang, sc, loc, TW_FINE, bg.shape, m.shape, asp)
        G = np.array([[tr.a, tr.b, tr.c], [tr.d, tr.e, tr.f], [0, 0, 1]]) @ H   # captura → UTM
        c = cells[cells.page == pno].copy()
        u = (c.x - rect.x0) / rect.width * bg.shape[1]
        v = (c.y - rect.y0) / rect.height * bg.shape[0]
        xy = G @ np.vstack([u, v, np.ones(len(c))])
        c["E"], c["N"] = xy[0], xy[1]
        c["crs"] = crs.to_string()
        c["ref_flight"] = f
        # ejes de la grilla en UTM (dirección de filas y de columnas de la captura)
        ex = G[:2, 0] / np.linalg.norm(G[:2, 0]); ey = G[:2, 1] / np.linalg.norm(G[:2, 1])
        c["ux_E"], c["ux_N"], c["uy_E"], c["uy_N"] = ex[0], ex[1], ey[0], ey[1]
        centers.append(c)
        px_m = np.linalg.norm(G[:2, 0])
        regs.append(dict(page=pno, year=year, site=site, status="OK", ref_flight=f, angle=ang, scale=sc, aspect=asp, cc=cc,
                         rot_description=rot0, bg_px_m=px_m, n_cells=len(c)))
        print(f"pág {pno} {year} {site}: {f} ang={ang:.2f} (Description {rot0}) asp={asp:.3f} cc={cc:.3f} "
              f"captura={px_m * 100:.1f} cm/px celdas={len(c)}")
    reg = pd.DataFrame(regs)
    reg.to_csv(OUTDIR / "registration.csv", index=False)
    cen = pd.concat(centers, ignore_index=True)
    cen.to_csv(OUTDIR / "plot_centers.csv", index=False)
    build_polygons(cen)


def build_polygons(cen: pd.DataFrame) -> None:
    out = []
    for (pno, crs), g in cen.groupby(["page", "crs"]):
        # espaciamiento: mediana de distancias a vecinos en fila (Δcol=1) y columna (Δrow=1)
        key = g.set_index(["map_row", "map_col"])[["E", "N"]]
        d_col, d_row = [], []
        for (r, c_), p in key.iterrows():
            if (r, c_ + 1) in key.index:
                d_col.append(np.linalg.norm(key.loc[(r, c_ + 1)].to_numpy() - p.to_numpy()))
            if (r + 1, c_) in key.index:
                d_row.append(np.linalg.norm(key.loc[(r + 1, c_)].to_numpy() - p.to_numpy()))
        pc, pr = np.median(d_col), np.median(d_row)
        ux = np.array([g.ux_E.iloc[0], g.ux_N.iloc[0]]); uy = np.array([g.uy_E.iloc[0], g.uy_N.iloc[0]])
        hx, hy = LEN_FRAC * pc / 2, WID_FRAC * pr / 2
        polys = [Polygon([(e + sx * hx * ux[0] + sy * hy * uy[0], n + sx * hx * ux[1] + sy * hy * uy[1])
                          for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]) for e, n in zip(g.E, g.N)]
        gg = gpd.GeoDataFrame(g.drop(columns=["crs"]), geometry=polys, crs=crs)
        gg["pitch_col_m"], gg["pitch_row_m"] = pc, pr
        out.append(gg.to_crs(32611))
        print(f"  pág {pno}: espaciamiento entre columnas {pc:.2f} m, entre filas {pr:.2f} m")
    grid = gpd.GeoDataFrame(pd.concat(out, ignore_index=True), crs=32611)
    grid["plot_uid"] = np.where(grid["kind"] == "plot",
                                grid.year.astype(str) + "_" + grid.site + "_" + grid.trial.astype(str) + "_P"
                                + grid["plot"].astype("Int64").astype(str).str.zfill(3), "")
    grid.to_file(OUTDIR / "plot_grid.gpkg", layer="plots", driver="GPKG")


if __name__ == "__main__":
    main()
