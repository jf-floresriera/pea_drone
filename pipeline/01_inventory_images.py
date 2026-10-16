"""Fase 1a - Inventario y control de calidad de los ortomosaicos multiespectrales.

Para cada .tif: integridad (lectura/0 bytes), CRS, GSD, extensión, nº de bandas, píxeles válidos
(banda alfa), saturación y estadísticos de DN sobre una lectura submuestreada.
Salidas: outputs/01_inventory/{image_inventory.csv, flight_inventory.csv, inventory_summary.md}
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling

sys.path.insert(0, str(Path(__file__).parent))
from config import BAND_ORDER, OUT, ROOT, parse_tif  # noqa: E402

DECIM = 8  # factor de submuestreo para estadísticos (≈ 64x menos píxeles)
OUTDIR = OUT / "01_inventory"


def describe(path: Path) -> dict:
    rec = parse_tif(path)
    rec["size_mb"] = round(path.stat().st_size / 2**20, 2)
    if path.stat().st_size == 0:
        rec.update(status="EMPTY_0_BYTES")
        return rec
    try:
        with rasterio.open(path) as r:
            h, w = max(1, r.height // DECIM), max(1, r.width // DECIM)
            data = r.read(out_shape=(r.count, h, w), resampling=Resampling.nearest)
            b = r.bounds
            rec.update(
                status="OK", width=r.width, height=r.height, count=r.count, dtype=r.dtypes[0],
                epsg=r.crs.to_epsg() if r.crs else None, gsd_m=round(r.res[0], 4),
                xmin=b.left, ymin=b.bottom, xmax=b.right, ymax=b.top,
                area_ha=round((b.right - b.left) * (b.top - b.bottom) / 1e4, 3),
                compress=r.profile.get("compress"), tiled=r.profile.get("tiled"),
            )
    except Exception as e:  # archivo corrupto
        rec.update(status=f"UNREADABLE: {e.__class__.__name__}")
        return rec

    dn = data[0].astype(np.float64)
    valid = data[1] > 0 if data.shape[0] > 1 else np.ones_like(dn, bool)
    v = dn[valid]
    rec["valid_frac"] = round(valid.mean(), 4)
    if v.size:
        p = np.percentile(v, [1, 5, 25, 50, 75, 95, 99])
        rec.update({f"p{q}": round(x, 1) for q, x in zip((1, 5, 25, 50, 75, 95, 99), p)})
        rec.update(mean=round(v.mean(), 1), std=round(v.std(), 1), dn_max=int(v.max()),
                   sat_frac=round(float((v >= 65535).mean()), 6), zero_frac=round(float((v == 0).mean()), 6))
    return rec


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    files = sorted(ROOT.glob("Images20*/**/*.tif"))
    print(f"{len(files)} archivos .tif")
    rows = []
    for i, f in enumerate(files, 1):
        rows.append(describe(f))
        if i % 25 == 0:
            print(f"  {i}/{len(files)}")
    df = pd.DataFrame(rows)
    df.to_csv(OUTDIR / "image_inventory.csv", index=False)

    # Tabla por vuelo: completitud de bandas y GSD
    df["ok"] = df["status"].eq("OK")
    fl = (df.groupby(["year", "site", "crop", "stage", "date", "flight_dir"])
            .agg(bands_ok=("ok", "sum"),
                 missing_bands=("band", lambda s: ",".join(sorted(set(BAND_ORDER) - set(s[df.loc[s.index, 'ok']])))),
                 gsd_m=("gsd_m", "median"), area_ha=("area_ha", "median"), size_mb=("size_mb", "sum"))
            .reset_index())
    fl["usable_all_bands"] = fl["bands_ok"].eq(5)
    fl.to_csv(OUTDIR / "flight_inventory.csv", index=False)

    with open(OUTDIR / "inventory_summary.md", "w", encoding="utf-8") as fh:
        fh.write("# Inventario de ortomosaicos\n\n")
        fh.write(f"- Archivos: {len(df)} | OK: {df.ok.sum()} | vacíos/ilegibles: {(~df.ok).sum()}\n")
        fh.write(f"- Vuelos: {len(fl)} | con 5 bandas completas: {fl.usable_all_bands.sum()}\n")
        fh.write(f"- Volumen total: {df.size_mb.sum()/1024:.2f} GB\n")
        fh.write(f"- CRS: {sorted(df.epsg.dropna().astype(int).unique().tolist())}\n")
        fh.write(f"- GSD (m): min {df.gsd_m.min():.4f}, mediana {df.gsd_m.median():.4f}, max {df.gsd_m.max():.4f}\n\n")
        fh.write("## Vuelos\n\n" + fl.drop(columns=["flight_dir"]).to_markdown(index=False) + "\n\n")
        bad = df.loc[~df.ok, ["path", "status"]]
        fh.write(f"## Archivos con problemas ({len(bad)})\n\n" + bad.to_markdown(index=False) + "\n")
    print(fl.to_string())


if __name__ == "__main__":
    main()
