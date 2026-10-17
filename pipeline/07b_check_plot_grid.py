"""Fase 2.4c - Verificación de la grilla georreferenciada.

Para cada campo: superposición de los polígonos sobre el mosaico CIR del vuelo de referencia y métrica cuantitativa
de alineación:
  fracción de vegetación dentro del polígono vs. en un anillo exterior de 0,5 m (calles).
  Vegetación = NDVI con DN > umbral de Otsu del vuelo (solo para la verificación geométrica).
Si la grilla está bien puesta, la vegetación dentro >> la del anillo en fechas con el dosel desarrollado.
Refinamiento afín: se optimizan traslación (E, N), rotación y escala independiente en los dos ejes de la grilla
(sx a lo largo de las parcelas, sy entre filas), maximizando el contraste dentro-anillo, por búsqueda coordenada con
pasos decrecientes desde varios puntos de partida de escala (corrige capturas del croquis estiradas en x/y).
Salidas: outputs/07_plot_grid/{check/<pag>.png, alignment.csv, plot_grid_refined.gpkg}
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
import rasterio.features  # noqa: E402
from shapely.affinity import translate  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT, ROOT  # noqa: E402

OUTDIR = OUT / "07_plot_grid"
NOM_COL, NOM_ROW = 6.1, 2.0
DEC = 4  # submuestreo (≈7-12 cm)
TRIAL_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6", "#e34948"]


def otsu(x):
    h, e = np.histogram(x, 256); m = (e[:-1] + e[1:]) / 2
    w0 = np.cumsum(h); w1 = w0[-1] - w0
    m0 = np.cumsum(h * m) / np.maximum(w0, 1); m1 = (np.sum(h * m) - np.cumsum(h * m)) / np.maximum(w1, 1)
    return m[np.argmax(w0 * w1 * (m0 - m1) ** 2)]


def read(flight, inv, band):
    r = inv[(inv.flight_dir == flight) & (inv.band == band) & (inv.status == "OK")]
    if r.empty:
        return None, None
    with rasterio.open(ROOT / r.iloc[0].path) as s:
        a = s.read(1, out_shape=(s.height // DEC, s.width // DEC)).astype(np.float32)
        tr = s.transform * s.transform.scale(s.width / a.shape[1], s.height / a.shape[0])
    return np.where(a > 0, a, np.nan), tr


def contrast(veg, tr, polys, dx=0.0, dy=0.0):
    inner = [translate(p, dx, dy) for p in polys] if (dx or dy) else polys
    ring = [p.buffer(0.5).difference(p) for p in inner]
    m_in = rasterio.features.rasterize([(p, 1) for p in inner], veg.shape, transform=tr) == 1
    m_ring = rasterio.features.rasterize([(p, 1) for p in ring], veg.shape, transform=tr) == 1
    m_ring &= ~m_in
    if not m_in.any() or not m_ring.any():
        return np.nan, np.nan, -1.0
    vi, vr = np.nanmean(veg[m_in]), np.nanmean(veg[m_ring])
    return vi, vr, (vi - vr) if np.isfinite(vi - vr) else -1.0


def polys_from(params, C, c0, ux, uy, hx, hy):
    """params = (tE, tN, rot°, sx, sy). Centros: c0 + Rot·B·diag(sx,sy)·Bᵀ·(C − c0) + t, con B = [ux uy]."""
    tE, tN, rot, sx, sy = params
    B = np.column_stack([ux, uy])
    r = np.radians(rot)
    Rm = np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])
    A = Rm @ B @ np.diag([sx, sy]) @ B.T
    P = (C - c0) @ A.T + c0 + np.array([tE, tN])
    ax, ay = Rm @ ux, Rm @ uy
    hxs, hys = hx * sx, hy * sy
    return [Polygon([tuple(p + a * hxs * ax + b * hys * ay) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            for p in P], P


def make_sampler(veg, tr, C, c0, ux, uy, hx, hy):
    """Contraste rápido por muestreo de puntos: 9×3 puntos dentro de cada parcela y puntos 0,4 m fuera de sus
    cuatro lados (calles), leídos del ráster de vegetación. Equivalente al contraste rasterizado, pero vectorizado."""
    inv = ~tr
    a_in, b_in = np.meshgrid(np.linspace(-0.85, 0.85, 9), np.linspace(-0.7, 0.7, 3))
    a_in, b_in = a_in.ravel(), b_in.ravel()
    lin = np.linspace(-0.8, 0.8, 5)

    def f(q):
        tE, tN, rot, sx, sy = q
        r = np.radians(rot)
        Rm = np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])
        B = np.column_stack([ux, uy])
        P = (C - c0) @ (Rm @ B @ np.diag([sx, sy]) @ B.T).T + c0 + np.array([tE, tN])
        ax, ay = Rm @ ux, Rm @ uy
        hxs, hys = hx * sx, hy * sy
        dx, dy = 1 + 0.4 / hxs, 1 + 0.4 / hys
        a_r = np.concatenate([np.full(5, -dx), np.full(5, dx), lin, lin])
        b_r = np.concatenate([lin, lin, np.full(5, -dy), np.full(5, dy)])

        def sample(a, b):
            pts = P[:, None, :] + a[None, :, None] * hxs * ax + b[None, :, None] * hys * ay
            col, row = inv * (pts[..., 0].ravel(), pts[..., 1].ravel())
            col, row = np.floor(col).astype(int), np.floor(row).astype(int)
            ok = (row >= 0) & (row < veg.shape[0]) & (col >= 0) & (col < veg.shape[1])
            v = np.full(row.shape, np.nan, np.float32)
            v[ok] = veg[row[ok], col[ok]]
            return np.nanmean(v) if np.isfinite(v).any() else np.nan
        d = sample(a_in, b_in) - sample(a_r, b_r)
        return d if np.isfinite(d) else -1.0
    return f


def refine(veg, tr, C, c0, ux, uy, hx, hy, pitch_x, pitch_y, s0=(1.0, 1.0)):
    f = make_sampler(veg, tr, C, c0, ux, uy, hx, hy)
    best_q = np.array([0, 0, 0, *s0]); best_v = f(best_q)
    # Puntos de partida en escala alrededor del prior s0, con búsqueda de traslación de ±medio espaciamiento
    for sx in s0[0] * np.geomspace(0.8, 1.25, 12):
        for sy in s0[1] * np.geomspace(0.8, 1.25, 12):
            for tx in np.linspace(-pitch_x / 2, pitch_x / 2, 7):
                for ty in np.linspace(-pitch_y / 2, pitch_y / 2, 7):
                    q = np.array([tx * ux[0] + ty * uy[0], tx * ux[1] + ty * uy[1], 0, sx, sy])
                    v = f(q)
                    if v > best_v:
                        best_q, best_v = q, v
    steps = np.array([0.4, 0.4, 0.4, 0.03, 0.03])
    for _ in range(7):
        improved = True
        while improved:
            improved = False
            for i in range(5):
                for sgn in (-1, 1):
                    q = best_q.copy(); q[i] += sgn * steps[i]
                    v = f(q)
                    if v > best_v + 1e-4:
                        best_q, best_v, improved = q, v, True
        steps /= 2
    return best_q, best_v


def main() -> None:
    (OUTDIR / "check").mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    grid = gpd.read_file(OUTDIR / "plot_grid.gpkg", layer="plots")
    reg = pd.read_csv(OUTDIR / "registration.csv")
    rows, refined = [], []
    global NOM_COL, NOM_ROW
    pp = grid.groupby("page")[["pitch_col_m", "pitch_row_m"]].first()
    NOM_COL, NOM_ROW = float(pp.pitch_col_m.median()), float(pp.pitch_row_m.median())
    print(f"espaciamiento nominal (mediana de campos): {NOM_COL:.2f} × {NOM_ROW:.2f} m")
    for _, rg in reg[reg.status == "OK"].iterrows():
        g = grid[grid.page == rg.page].copy()
        nir, tr = read(rg.ref_flight, inv, "nir")
        red, _ = read(rg.ref_flight, inv, "red")
        green, _ = read(rg.ref_flight, inv, "green")
        with rasterio.open(ROOT / inv[(inv.flight_dir == rg.ref_flight) & (inv.band == "red")].iloc[0].path) as s:
            crs = s.crs
        gl = g.to_crs(crs)
        nd = (nir - red) / (nir + red)
        veg = (nd > otsu(nd[np.isfinite(nd)])).astype(np.float32)
        veg[~np.isfinite(nd)] = np.nan
        plots = gl[gl.kind == "plot"]
        vi0, vr0, c0_ = contrast(veg, tr, list(plots.geometry))
        cen = gl.geometry.centroid
        C = np.column_stack([cen.x, cen.y])
        c0 = C.mean(axis=0)
        ux = np.array([gl.ux_E.iloc[0], gl.ux_N.iloc[0]]); uy = np.array([gl.uy_E.iloc[0], gl.uy_N.iloc[0]])
        px, py = gl.pitch_col_m.iloc[0], gl.pitch_row_m.iloc[0]
        hx, hy = 0.80 * px / 2, 0.70 * py / 2
        is_plot = (gl.kind == "plot").to_numpy()
        # Prior físico: todos los ensayos comparten el diseño de parcela (6,1 × 1,5 m + calles; Zhang et al. 2021).
        # Si el espaciamiento registrado se aleja >20 % de la mediana de los demás campos (aliasing por franjas dentro
        # de la parcela), se reescala a esa mediana antes de optimizar.
        s0 = (NOM_COL / px if abs(px / NOM_COL - 1) > 0.2 else 1.0, NOM_ROW / py if abs(py / NOM_ROW - 1) > 0.2 else 1.0)
        if s0 != (1.0, 1.0):
            print(f"   prior físico: espaciamiento {px:.2f}×{py:.2f} m → escala inicial ({s0[0]:.2f}, {s0[1]:.2f})")
        q, _ = refine(veg, tr, C[is_plot], c0, ux, uy, hx, hy, px * s0[0], py * s0[1], s0)
        polys, P = polys_from(q, C, c0, ux, uy, hx, hy)
        gl["geometry"] = polys
        gl["E"], gl["N"] = P[:, 0], P[:, 1]
        gl["pitch_col_m"], gl["pitch_row_m"] = px * q[3], py * q[4]
        vi1, vr1, c1 = contrast(veg, tr, [p for p, k in zip(polys, is_plot) if k])
        refined.append(gl.to_crs(32611))
        rows.append(dict(page=rg.page, year=rg.year, site=rg.site, ref_flight=rg.ref_flight, cc=rg.cc,
                         veg_in_before=vi0, veg_ring_before=vr0, contrast_before=c0_, tE=q[0], tN=q[1], rot=q[2],
                         sx=q[3], sy=q[4], pitch_col_m=px * q[3], pitch_row_m=py * q[4], veg_in=vi1, veg_ring=vr1,
                         contrast=c1, n_plots=int(is_plot.sum())))
        print(f"pág {rg.page} {rg.year} {rg.site}: contraste {c0_:.2f} → {c1:.2f} (dentro {vi1:.2f}, anillo {vr1:.2f}) "
              f"t=({q[0]:+.2f},{q[1]:+.2f}) m rot={q[2]:+.2f}° sx={q[3]:.3f} sy={q[4]:.3f} "
              f"→ espaciamiento {px * q[3]:.2f} × {py * q[4]:.2f} m")

        # Figura: CIR + polígonos por ensayo
        def st(a):
            lo, hi = np.nanpercentile(a, [2, 98]); return np.clip((a - lo) / (hi - lo), 0, 1)
        g3 = green if green is not None else red  # vuelos parciales sin verde
        cir = np.dstack([st(nir), st(red), st(g3)]); cir[~np.isfinite(nir)] = 1
        ext = (tr.c, tr.c + tr.a * nir.shape[1], tr.f + tr.e * nir.shape[0], tr.f)
        fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
        b = gl.total_bounds
        for ax, zoom in zip(axes, (False, True)):
            ax.imshow(cir, extent=ext, interpolation="nearest")
            for i, (t, gt) in enumerate(gl[gl.kind == "plot"].groupby("trial")):
                gt.boundary.plot(ax=ax, color=TRIAL_COLORS[i % 7], lw=0.6 if not zoom else 1.0, label=t)
            gl[gl.kind != "plot"].boundary.plot(ax=ax, color="white", lw=0.4, linestyle=":")
            if zoom:
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                ax.set_xlim(cx - 12, cx + 12); ax.set_ylim(cy - 12, cy + 12)
                for _, p in gl[gl.kind == "plot"].cx[cx - 12:cx + 12, cy - 12:cy + 12].iterrows():
                    c_ = p.geometry.centroid
                    ax.text(c_.x, c_.y, f"{p.trial}\n{int(p['plot'])}", fontsize=5, ha="center", va="center",
                            color="white")
            else:
                ax.set_xlim(b[0] - 5, b[2] + 5); ax.set_ylim(b[1] - 5, b[3] + 5)
                ax.legend(fontsize=6, loc="upper right", frameon=True)
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f"p{rg.page} {rg.year} {rg.site} - {rg.ref_flight} - contraste dentro/anillo {c1:.2f}",
                     fontsize=9, x=0.01, ha="left")
        fig.savefig(OUTDIR / "check" / f"p{int(rg.page):02d}_{rg.year}_{rg.site}.png", dpi=130, bbox_inches="tight")
        plt.close(fig)
    pd.DataFrame(rows).to_csv(OUTDIR / "alignment.csv", index=False)
    gpd.GeoDataFrame(pd.concat(refined, ignore_index=True), crs=32611).to_file(
        OUTDIR / "plot_grid_refined.gpkg", layer="plots", driver="GPKG")


if __name__ == "__main__":
    main()
