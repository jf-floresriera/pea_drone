"""Fase 2.2 - Calibración radiométrica cruzada UAV → Sentinel-2 L2A (reflectancia de superficie).

Motivo: los ortomosaicos `transparent_mosaic` están en DN (12 bit × 16) y el panel de reflectancia no aparece en ellos
(las dianas GCP blancas saturan). Se aplica una línea empírica por banda y por vuelo, con Sentinel-2 L2A como
referencia de reflectancia:

    ρ_S2(píxel 10/20 m) = ganancia · DN̄_UAV(píxel) + offset

donde DN̄ es la media de los DN UAV dentro de cada píxel S2 (los DN y la radiancia son lineales y la mezcla
suelo-dosel también lo es, por lo que el modelo lineal es válido a escala de píxel S2).

Correspondencia de bandas (RedEdge → MSI): blue 475→B02 490, green 560→B03 560, red 668→B04 665,
red edge 717→B05 705 (20 m), nir 840→B08 842.

Selección de escena: Planetary Computer `sentinel-2-l2a`, |Δt| ≤ 6 días, la más cercana con ≥95 % de los píxeles de
la huella en las clases SCL 4/5 (vegetación / suelo desnudo).
Píxeles usados: cobertura UAV completa (fracción válida ≥ 0.999) y SCL 4/5.
Ajuste: Huber (robusto) + R², RMSE y RMSE por validación cruzada de 5 particiones.

Salidas: outputs/05_radiometric/{calibration_coefficients.csv, scatter/<vuelo>.png, calibration_summary.md}
Los mosaicos calibrados no se escriben (falta disco); los coeficientes se aplican al extraer rasgos (Fase 3).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import planetary_computer as pc  # noqa: E402
import pystac_client  # noqa: E402
import rasterio  # noqa: E402
import rasterio.features  # noqa: E402
from rasterio.warp import Resampling, reproject, transform_bounds  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402
from sklearn.linear_model import HuberRegressor  # noqa: E402
from sklearn.model_selection import KFold  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import BAND_ORDER, OUT, ROOT  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning)
OUTDIR = OUT / "05_radiometric"
S2_BAND = {"blue": "B02", "green": "B03", "red": "B04", "red edge": "B05", "nir": "B08"}
MAX_DT = 6
MIN_CLEAR = 0.95
INK, MUTED = "#0b0b0b", "#52514e"
BAND_COL = {"blue": "#2a78d6", "green": "#1baf7a", "red": "#e34948", "red edge": "#6250d6", "nir": "#52514e"}

CATALOG = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                    modifier=pc.sign_inplace)


def boa_offset(item) -> float:
    """Desde el baseline 04.00 (ene-2022) L2A trae BOA_ADD_OFFSET = -1000."""
    try:
        return -1000.0 if float(item.properties.get("s2:processing_baseline", "0")) >= 4.0 else 0.0
    except ValueError:
        return 0.0


def read_s2(href: str, bounds_utm, crs_utm):
    with rasterio.open(href) as src:
        b = transform_bounds(crs_utm, src.crs, *bounds_utm) if src.crs != crs_utm else bounds_utm
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win, boundless=True, fill_value=0).astype(np.float32)
        return arr, src.window_transform(win), src.crs


def pick_scene(footprint_utm, crs_utm, date: pd.Timestamp):
    lonlat = gpd.GeoSeries([footprint_utm], crs=crs_utm).to_crs(4326).iloc[0]
    items = list(CATALOG.search(collections=["sentinel-2-l2a"], intersects=lonlat.centroid.__geo_interface__,
                                datetime=f"{(date - pd.Timedelta(days=MAX_DT)).date()}/"
                                         f"{(date + pd.Timedelta(days=MAX_DT)).date()}").items())
    items.sort(key=lambda i: abs((pd.Timestamp(i.datetime.date()) - date).days))
    for it in items:
        scl, tr, crs = read_s2(it.assets["SCL"].href, footprint_utm.bounds, crs_utm)
        inside = rasterio.features.geometry_mask([footprint_utm.__geo_interface__], scl.shape, tr, invert=True)
        if not inside.any():
            continue
        clear = np.isin(scl[inside], (4, 5)).mean()
        if clear >= MIN_CLEAR:
            return it, float(clear)
    return None, np.nan


def uav_to_s2_grid(path: Path, s2_shape, s2_tr, s2_crs):
    with rasterio.open(path) as r:
        d = r.read()
        dn = d[0].astype(np.float32)
        valid = (d[-1] > 0) if r.count > 1 else (d[0] > 0)
        src_tr, src_crs = r.transform, r.crs
    dn_avg = np.zeros(s2_shape, np.float32)
    cov = np.zeros(s2_shape, np.float32)
    reproject(np.where(valid, dn, np.nan), dn_avg, src_transform=src_tr, src_crs=src_crs, dst_transform=s2_tr,
              dst_crs=s2_crs, resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
    reproject(valid.astype(np.float32), cov, src_transform=src_tr, src_crs=src_crs, dst_transform=s2_tr,
              dst_crs=s2_crs, resampling=Resampling.average, dst_nodata=0)
    return dn_avg, cov


def fit(x, y):
    hub = HuberRegressor(epsilon=1.5, max_iter=500).fit(x[:, None], y)
    pred = hub.predict(x[:, None])
    ss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - pred) ** 2).sum() / ss if ss > 0 else np.nan
    cv = []
    for tr_i, te_i in KFold(5, shuffle=True, random_state=0).split(x):
        h = HuberRegressor(epsilon=1.5, max_iter=500).fit(x[tr_i, None], y[tr_i])
        cv.append(((y[te_i] - h.predict(x[te_i, None])) ** 2).mean())
    return hub.coef_[0], hub.intercept_, r2, float(np.sqrt(((y - pred) ** 2).mean())), float(np.sqrt(np.mean(cv)))


def main() -> None:
    (OUTDIR / "scatter").mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"].copy()
    inv["date"] = pd.to_datetime(inv["date"])
    done = set()
    coef_path = OUTDIR / "calibration_coefficients.csv"
    rows = pd.read_csv(coef_path).to_dict("records") if coef_path.exists() else []
    done = {(r["flight_dir"], r["band"]) for r in rows}

    for fdir, g in inv.groupby("flight_dir"):
        g = g.set_index("band")
        if all((fdir, b) in done for b in g.index):
            continue
        ref = ROOT / g.iloc[0].path
        with rasterio.open(ref) as r:
            dec = r.read(r.count, out_shape=(r.height // 16, r.width // 16)) > 0 if r.count > 1 else \
                r.read(1, out_shape=(r.height // 16, r.width // 16)) > 0
            tr16 = r.transform * r.transform.scale(16, 16)
            crs_utm = r.crs
        from shapely.geometry import shape
        from shapely.ops import unary_union
        fp = unary_union([shape(s) for s, v in rasterio.features.shapes(dec.astype(np.uint8), mask=dec,
                                                                         transform=tr16) if v == 1])
        meta = g.iloc[0]
        item, clear = pick_scene(fp, crs_utm, meta.date)
        if item is None:
            print(f"{fdir}: sin escena S2 despejada a ±{MAX_DT} d")
            for b in g.index:
                rows.append(dict(year=meta.year, site=meta.site, crop=meta.crop, stage=meta.stage,
                                 date=meta.date.date(), flight_dir=fdir, band=b, status="NO_S2_SCENE"))
            continue
        s2_date = pd.Timestamp(item.datetime.date())
        fig, axes = plt.subplots(1, len(g), figsize=(2.2 * len(g), 2.3), squeeze=False)
        for ax, b in zip(axes[0], [x for x in BAND_ORDER if x in g.index]):
            s2, s2_tr, s2_crs = read_s2(item.assets[S2_BAND[b]].href, fp.bounds, crs_utm)
            scl, scl_tr, _ = read_s2(item.assets["SCL"].href, fp.bounds, crs_utm)
            scl_on = np.zeros(s2.shape, np.float32)
            reproject(scl, scl_on, src_transform=scl_tr, src_crs=s2_crs, dst_transform=s2_tr, dst_crs=s2_crs,
                      resampling=Resampling.nearest)
            dn, cov = uav_to_s2_grid(ROOT / g.loc[b].path, s2.shape, s2_tr, s2_crs)
            rho = (s2 + boa_offset(item)) / 10000.0
            ok = (cov >= 0.999) & np.isfinite(dn) & np.isin(scl_on, (4, 5)) & (s2 > 0)
            x, y = dn[ok], rho[ok]
            rec = dict(year=meta.year, site=meta.site, crop=meta.crop, stage=meta.stage, date=meta.date.date(),
                       flight_dir=fdir, band=b, s2_band=S2_BAND[b], s2_id=item.id, s2_date=s2_date.date(),
                       dt_days=(s2_date - meta.date).days, clear_frac=round(clear, 3), n_px=int(ok.sum()))
            if ok.sum() < 15:
                rec["status"] = "FEW_PIXELS"
            else:
                a, c, r2, rmse, cv = fit(x, y)
                rec.update(status="OK", gain=a, offset=c, r2=r2, rmse=rmse, cv_rmse=cv,
                           rho_min=float(y.min()), rho_max=float(y.max()))
                xx = np.linspace(x.min(), x.max(), 10)
                ax.scatter(x / 65520, y, s=6, color=BAND_COL[b], alpha=0.6, lw=0)
                ax.plot(xx / 65520, a * xx + c, color=INK, lw=1)
                ax.text(0.04, 0.96, f"R²={r2:.2f}\nRMSE={rmse:.3f}\nn={ok.sum()}", transform=ax.transAxes,
                        va="top", fontsize=6, color=INK)
            ax.set_title(f"{b} → {S2_BAND[b]}", fontsize=7, color=INK)
            ax.set_xlabel("DN UAV / 65520", fontsize=6); ax.tick_params(labelsize=6)
            ax.spines[["top", "right"]].set_visible(False)
            rows.append(rec)
        axes[0, 0].set_ylabel("ρ Sentinel-2 L2A", fontsize=6)
        fig.suptitle(f"{fdir} ({meta.date.date()}) vs {item.id[:24]} (Δt={(s2_date - meta.date).days} d)",
                     fontsize=7, x=0.01, ha="left", color=INK)
        fig.savefig(OUTDIR / "scatter" / f"{meta.year}_{fdir}.png", dpi=150, bbox_inches="tight"); plt.close(fig)
        pd.DataFrame(rows).to_csv(coef_path, index=False)
        ok_r = [r for r in rows if r.get("flight_dir") == fdir and r.get("status") == "OK"]
        print(f"{fdir}: S2 {s2_date.date()} (Δt={(s2_date - meta.date).days} d, clear={clear:.2f}) "
              + " ".join(f"{r['band']}:R²={r['r2']:.2f}" for r in ok_r))

    co = pd.DataFrame(rows)
    co.to_csv(coef_path, index=False)
    ok = co[co.status == "OK"]
    with open(OUTDIR / "calibration_summary.md", "w", encoding="utf-8") as fh:
        fh.write("# Calibración cruzada UAV → Sentinel-2 L2A\n\n")
        fh.write(f"- Bandas-vuelo calibradas: {len(ok)} de {len(co)}\n")
        fh.write("- Estado:\n\n" + co.status.value_counts().to_frame().to_markdown() + "\n\n")
        fh.write("## Calidad por banda\n\n" + ok.groupby("band")[["r2", "rmse", "cv_rmse", "n_px", "dt_days"]]
                 .agg(["median", "min", "max"]).round(3).to_markdown() + "\n")
    print(ok.groupby("band")[["r2", "rmse", "cv_rmse"]].median().round(3))


if __name__ == "__main__":
    main()
