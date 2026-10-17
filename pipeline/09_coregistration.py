"""Fase 2.3 - Corregistro multitemporal de los ortomosaicos de cada campo.

La grilla de parcelas se georreferencia sobre un vuelo de referencia por campo (`07`). Para usar los mismos polígonos
en todas las fechas se estima el desfase (traslación) de cada vuelo respecto de la referencia:
  1. Ambos mosaicos se leen en una grilla UTM común de 5 cm sobre la intersección de huellas.
  2. Se usa el gradiente de la banda roja (bordes de parcelas y calles, estables aunque cambie el dosel).
  3. Correlación de fase con ventana de Hann (skimage.registration.phase_cross_correlation, precisión subpíxel 1/10).
  4. Control: desfases > 1 m se marcan como sospechosos y se repiten con NIR.
Los vuelos usaron GCP, por lo que se esperan desfases de pocos centímetros.
Salida: outputs/09_coregistration/coregistration.csv (shift_E_m, shift_N_m a sumar a la grilla para cada vuelo)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject
from scipy.ndimage import sobel
from skimage.registration import phase_cross_correlation

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT, ROOT  # noqa: E402

OUTDIR = OUT / "09_coregistration"
RES = 0.05


def on_grid(path: Path, bounds, res=RES):
    W, H = int((bounds[2] - bounds[0]) / res), int((bounds[3] - bounds[1]) / res)
    tr = from_origin(bounds[0], bounds[3], res, res)
    with rasterio.open(path) as s:
        out = np.full((H, W), np.nan, np.float32)
        d = s.read(1).astype(np.float32)
        valid = (s.read(s.count) > 0) if s.count > 1 else d > 0
        reproject(np.where(valid, d, np.nan), out, src_transform=s.transform, src_crs=s.crs, dst_transform=tr,
                  dst_crs=s.crs, resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
    return out


def edges(a):
    a = np.nan_to_num((a - np.nanmean(a)) / (np.nanstd(a) + 1e-6))
    return np.hypot(sobel(a, 0), sobel(a, 1))


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"]
    reg = pd.read_csv(OUT / "07_plot_grid" / "registration.csv")
    fl = pd.read_csv(OUT / "01_inventory" / "flight_inventory.csv")
    pages = {1: dict(crop="pea"), 2: dict(crop="pea"), 3: dict(crop="chickpea"), 4: dict(crop="pea"),
             5: dict(crop="chickpea"), 6: {}, 7: dict(crop="pea"), 8: dict(crop="chickpea"), 9: dict(crop="pea"),
             10: dict(crop="chickpea"), 11: {}, 12: dict(stage="advanced")}
    rows = []
    for _, rg in reg[reg.status == "OK"].iterrows():
        sel = fl[(fl.year == rg.year) & (fl.site == rg.site)]
        for k, v in pages[int(rg.page)].items():
            sel = sel[sel[k] == v]

        def path(f, band):
            r = inv[(inv.flight_dir == f) & (inv.band == band)]
            return ROOT / r.iloc[0].path if not r.empty else None
        ref_p = path(rg.ref_flight, "red")
        for f in sel.flight_dir:
            if f == rg.ref_flight:
                rows.append(dict(page=rg.page, year=rg.year, site=rg.site, flight_dir=f, ref_flight=rg.ref_flight,
                                 band="ref", shift_E_m=0.0, shift_N_m=0.0, error=0.0, status="REF"))
                continue
            for band in ("red", "nir"):
                p, pr = path(f, band), path(rg.ref_flight, band)
                if p is None or pr is None:
                    continue
                with rasterio.open(p) as a, rasterio.open(pr) as b:
                    ba, bb = a.bounds, b.bounds
                ib = (max(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), min(ba[3], bb[3]))
                # recorte central (60 %) de la intersección para evitar bordes del mosaico
                cx, cy, hw, hh = (ib[0] + ib[2]) / 2, (ib[1] + ib[3]) / 2, 0.3 * (ib[2] - ib[0]), 0.3 * (ib[3] - ib[1])
                box = (cx - hw, cy - hh, cx + hw, cy + hh)
                A, B = edges(on_grid(pr, box)), edges(on_grid(p, box))
                shift, err, _ = phase_cross_correlation(A, B, upsample_factor=10, normalization=None)
                dy_px, dx_px = shift  # desplazamiento a aplicar a B para alinearlo con A
                sE, sN = -dx_px * RES, dy_px * RES  # traslación de la grilla (en coordenadas de A) hacia B
                status = "OK" if np.hypot(sE, sN) <= 1.0 else "SOSPECHOSO"
                rows.append(dict(page=rg.page, year=rg.year, site=rg.site, flight_dir=f, ref_flight=rg.ref_flight,
                                 band=band, shift_E_m=round(sE, 3), shift_N_m=round(sN, 3), error=round(float(err), 4),
                                 status=status))
                print(f"p{rg.page} {f} ({band}): ΔE={sE:+.3f} ΔN={sN:+.3f} m [{status}]")
                if status == "OK":
                    break
    df = pd.DataFrame(rows)
    df.to_csv(OUTDIR / "coregistration.csv", index=False)
    ok = df[df.status == "OK"]
    print(f"\n{len(ok)} vuelos OK; desfase mediano {np.hypot(ok.shift_E_m, ok.shift_N_m).median():.3f} m, "
          f"máximo {np.hypot(ok.shift_E_m, ok.shift_N_m).max():.3f} m; sospechosos: {(df.status == 'SOSPECHOSO').sum()}")


if __name__ == "__main__":
    main()
