"""Fase 2.2 - Calibración radiométrica cruzada UAV → Sentinel-2 L2A con muestreo por sectores.

Motivo: los ortomosaicos `transparent_mosaic` están en DN (12 bit × 16), con valores físicamente imposibles como
reflectancia (ver docs/DATA_ISSUES.md, IMG-02), y el panel no aparece en los mosaicos. Se calibra contra la
reflectancia de superficie de Sentinel-2 L2A.

Problema de escala (2 cm vs 10-20 m). La comparación píxel a píxel mete ruido por:
  (i) el error de geolocalización de S2 (≈5-10 m), (ii) la PSF del MSI (cada píxel integra a sus vecinos) y
  (iii) la heterogeneidad parcela/calle en los bordes.
Diseño del muestreo por sectores:
  1. Grilla común = grilla S2 de 20 m (B05/SCL). Un **sector** = una celda de 20 m (2×2 píxeles de 10 m).
  2. UAV → grilla de 2 m alineada (media de DN válidos) → **convolución gaussiana que imita la PSF de S2**
     (σ = 4 m para bandas de 10 m y 8 m para B05; aproximación de MTF≈0.3 en Nyquist) → media por sector.
  3. **Búsqueda de desfase** entre UAV y S2 en ±2 píxeles de 10 m (máxima correlación conjunta NIR+rojo),
     común a todas las bandas del vuelo.
  4. **Filtro de sectores:** cobertura UAV completa, SCL 4/5 en todo el sector y homogeneidad interna
     (CV del NIR UAV a 2 m ≤ 0.25).
  5. **Estratos** por NDVI S2 del sector (suelo < 0.3 ≤ mezcla < 0.6 ≤ dosel), reportados para verificar que el
     ajuste cubra todo el rango.
Modelo (M2): ρ = b(año, banda) + g(vuelo, banda)·DN, ajuste robusto de Huber sobre los sectores de todos los vuelos
del año. b = nivel de negro común; g = exposición/iluminación del vuelo. Diagnóstico M1: ajuste libre por vuelo.

Correspondencia de bandas: blue→B02, green→B03, red→B04, red edge→B05 (20 m), nir→B08.
Escena: Planetary Computer `sentinel-2-l2a`, |Δt| ≤ 6 d, la más cercana con ≥95 % de la huella en SCL 4/5.
Salidas (outputs/05_radiometric/): sectors_uav_s2.csv.gz, calibration_per_flight.csv,
  calibration_coefficients.csv, plausibility.csv, calibration_summary.md, scatter/*.png
Los mosaicos calibrados no se escriben (falta disco); los coeficientes se aplican al extraer rasgos (Fase 3).
"""
from __future__ import annotations

import os
import shutil
import sys
import warnings
from pathlib import Path

# GDAL no decodifica rutas no-ASCII del bundle de certificados (p. ej. 'C:\Users\Jesús…\certifi\cacert.pem');
# se copia a una ruta ASCII del proyecto ANTES de importar rasterio.
import certifi  # noqa: E402
_CA = Path(__file__).resolve().parents[1] / "data_ext" / "cacert.pem"
_CA.parent.mkdir(exist_ok=True)
if not _CA.exists():
    shutil.copy(certifi.where(), _CA)
os.environ["GDAL_CURL_CA_BUNDLE"] = os.environ["CURL_CA_BUNDLE"] = str(_CA)
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

import geopandas as gpd  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import planetary_computer as pc  # noqa: E402
import pystac_client  # noqa: E402
import rasterio  # noqa: E402
import rasterio.features  # noqa: E402
from rasterio.transform import Affine  # noqa: E402
from rasterio.warp import Resampling, reproject  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402
from shapely.geometry import shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from sklearn.linear_model import HuberRegressor  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import BAND_ORDER, OUT, ROOT  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning)
OUTDIR = OUT / "05_radiometric"
S2_BAND = {"blue": "B02", "green": "B03", "red": "B04", "red edge": "B05", "nir": "B08"}
PSF_SIGMA_M = {"blue": 4.0, "green": 4.0, "red": 4.0, "nir": 4.0, "red edge": 8.0}
MAX_DT, MIN_CLEAR = 6, 0.95
MARGIN = 2          # píxeles de 10 m de margen para buscar desfase
FINE = 2.0          # m, grilla intermedia del UAV
MAX_CV = 0.25       # homogeneidad interna del sector (NIR a 2 m)
INK = "#0b0b0b"
STRATA_COL = {"suelo": "#eb6834", "mezcla": "#2a78d6", "dosel": "#1baf7a"}

CATALOG = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                    modifier=pc.sign_inplace)


def boa_offset(item) -> float:
    """Desde el baseline 04.00 (ene-2022) L2A trae BOA_ADD_OFFSET = -1000."""
    try:
        return -1000.0 if float(item.properties.get("s2:processing_baseline", "0")) >= 4.0 else 0.0
    except ValueError:
        return 0.0


def footprint(path: Path):
    with rasterio.open(path) as r:
        k = 16
        a = r.read(r.count, out_shape=(r.height // k, r.width // k)) > 0 if r.count > 1 else \
            r.read(1, out_shape=(r.height // k, r.width // k)) > 0
        tr = r.transform * r.transform.scale(r.width / a.shape[1], r.height / a.shape[0])
        fp = unary_union([shape(s) for s, v in rasterio.features.shapes(a.astype(np.uint8), mask=a, transform=tr)
                          if v == 1])
        return fp, r.crs


def s2_grid(item, fp, crs):
    """Ventana sobre la grilla de 20 m (B05) con margen; devuelve transformaciones de 20 y 10 m alineadas."""
    with rasterio.open(item.assets["B05"].href) as src:
        assert src.crs == crs, f"CRS S2 {src.crs} ≠ UAV {crs}"
        m = MARGIN * 10
        b = fp.bounds
        win = from_bounds(b[0] - m, b[1] - m, b[2] + m, b[3] + m, transform=src.transform)
        win = win.round_offsets().round_lengths()
        return win, src.window_transform(win)


def read_s2_band(item, asset: str, win20, tr20, shape10):
    """Lee un asset S2 en la ventana (definida en 20 m) y lo entrega en la grilla de 10 m."""
    with rasterio.open(item.assets[asset].href) as src:
        if src.res[0] == 20:
            a = src.read(1, window=win20, boundless=True, fill_value=0).astype(np.float32)
            return np.kron(a, np.ones((2, 2), np.float32))[:shape10[0], :shape10[1]]
        b = (tr20.c, tr20.f + tr20.e * win20.height, tr20.c + tr20.a * win20.width, tr20.f)  # límites geográficos
        w = from_bounds(*b, transform=src.transform).round_offsets()
        w = rasterio.windows.Window(w.col_off, w.row_off, shape10[1], shape10[0])
        return src.read(1, window=w, boundless=True, fill_value=0).astype(np.float32)


def pick_scene(fp, crs, date: pd.Timestamp):
    lonlat = gpd.GeoSeries([fp], crs=crs).to_crs(4326).iloc[0]
    items = list(CATALOG.search(collections=["sentinel-2-l2a"], intersects=lonlat.centroid.__geo_interface__,
                                datetime=f"{(date - pd.Timedelta(days=MAX_DT)).date()}/"
                                         f"{(date + pd.Timedelta(days=MAX_DT)).date()}").items())
    items.sort(key=lambda i: abs((pd.Timestamp(i.datetime.date()) - date).days))
    for it in items:
        win20, tr20 = s2_grid(it, fp, crs)
        with rasterio.open(it.assets["SCL"].href) as src:
            scl = src.read(1, window=win20, boundless=True, fill_value=0)
        inside = rasterio.features.geometry_mask([fp.__geo_interface__], scl.shape, tr20, invert=True)
        if inside.any() and np.isin(scl[inside], (4, 5)).mean() >= MIN_CLEAR:
            return it, float(np.isin(scl[inside], (4, 5)).mean())
    return None, np.nan


def uav_fine(path: Path, tr_fine: Affine, shape_fine):
    """DN medio y fracción válida del UAV en la grilla fina (2 m) alineada a S2."""
    with rasterio.open(path) as r:
        d = r.read()
        valid = (d[-1] > 0) if r.count > 1 else (d[0] > 0)
        dn = np.where(valid, d[0].astype(np.float32), np.nan)
        src_tr, crs = r.transform, r.crs
    out, cov = np.full(shape_fine, np.nan, np.float32), np.zeros(shape_fine, np.float32)
    reproject(dn, out, src_transform=src_tr, src_crs=crs, dst_transform=tr_fine, dst_crs=crs,
              resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
    reproject(valid.astype(np.float32), cov, src_transform=src_tr, src_crs=crs, dst_transform=tr_fine, dst_crs=crs,
              resampling=Resampling.average, dst_nodata=0)
    return out, cov


def psf_blur(a: np.ndarray, sigma_px: float) -> np.ndarray:
    """Convolución gaussiana normalizada (ignora NaN)."""
    w = np.isfinite(a).astype(np.float32)
    num = gaussian_filter(np.nan_to_num(a), sigma_px, mode="constant")
    den = gaussian_filter(w, sigma_px, mode="constant")
    return np.where(den > 1e-3, num / np.maximum(den, 1e-6), np.nan)


def block(a: np.ndarray, k: int, how: str = "mean") -> np.ndarray:
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    v = a[:h, :w].reshape(h // k, k, w // k, k)
    return {"mean": np.nanmean, "min": np.nanmin, "std": np.nanstd}[how](v, axis=(1, 3))


def extract_flight(fdir: str, g: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    meta = g.iloc[0]
    fp, crs = footprint(ROOT / meta.path)
    item, clear = pick_scene(fp, crs, meta.date)
    if item is None:
        return pd.DataFrame(), dict(flight_dir=fdir, status="NO_S2_SCENE")
    win20, tr20 = s2_grid(item, fp, crs)
    H10, W10 = int(win20.height) * 2, int(win20.width) * 2
    tr10 = tr20 * Affine.scale(0.5)
    # Núcleo (sin margen) en 10 m y su grilla fina de 2 m
    core = (H10 - 2 * MARGIN, W10 - 2 * MARGIN)
    tr_core10 = tr10 * Affine.translation(MARGIN, MARGIN)
    kf = int(10 / FINE)
    tr_fine = tr_core10 * Affine.scale(1 / kf)
    shape_fine = (core[0] * kf, core[1] * kf)

    s2 = {b: (read_s2_band(item, S2_BAND[b], win20, tr20, (H10, W10)) + boa_offset(item)) / 1e4
          for b in g.band.unique()}
    scl = read_s2_band(item, "SCL", win20, tr20, (H10, W10))
    uav, raw, cov = {}, {}, None
    for b, r in g.set_index("band").iterrows():
        dn, c = uav_fine(ROOT / r.path, tr_fine, shape_fine)
        raw[b] = dn
        uav[b] = block(psf_blur(dn, PSF_SIGMA_M[b] / FINE), kf)  # PSF-matched a 10 m
        cov = block(c, kf, "min") if cov is None else np.minimum(cov, block(c, kf, "min"))

    # Desfase: máxima correlación conjunta NIR + rojo (o la primera banda disponible)
    ref_b = [b for b in ("nir", "red") if b in uav] or [next(iter(uav))]
    best, best_r = (0, 0), -np.inf
    for dy in range(-MARGIN, MARGIN + 1):
        for dx in range(-MARGIN, MARGIN + 1):
            rs = []
            for b in ref_b:
                s = s2[b][MARGIN + dy:MARGIN + dy + core[0], MARGIN + dx:MARGIN + dx + core[1]]
                ok = (cov >= 0.999) & np.isfinite(uav[b]) & (s > 0)
                if ok.sum() > 10:
                    rs.append(np.corrcoef(uav[b][ok], s[ok])[0, 1])
            if rs and np.mean(rs) > best_r:
                best, best_r = (dy, dx), float(np.mean(rs))
    dy, dx = best
    sl = (slice(MARGIN + dy, MARGIN + dy + core[0]), slice(MARGIN + dx, MARGIN + dx + core[1]))

    # Sectores de 20 m = bloques 2×2 de 10 m
    sec = {}
    full = block((cov >= 0.999).astype(np.float32), 2, "min") == 1
    sclok = block(np.isin(scl[sl], (4, 5)).astype(np.float32), 2, "min") == 1
    ref_nir = raw.get("nir", next(iter(raw.values())))
    kk = kf * 2
    cv = block(ref_nir, kk, "std") / block(ref_nir, kk, "mean")
    for b in uav:
        sec[f"dn_{b}"] = block(uav[b], 2)
        sec[f"rho_{b}"] = block(s2[b][sl], 2)
    rows, cols = np.indices(full.shape)
    df = pd.DataFrame({k: v.ravel() for k, v in sec.items()})
    df["row"], df["col"], df["cv_nir"] = rows.ravel(), cols.ravel(), cv.ravel()
    df["keep"] = full.ravel() & sclok.ravel() & (df.cv_nir <= MAX_CV)
    if "rho_nir" in df and "rho_red" in df:
        nd = (df.rho_nir - df.rho_red) / (df.rho_nir + df.rho_red)
        df["stratum"] = np.select([nd < 0.3, nd < 0.6], ["suelo", "mezcla"], "dosel")
    else:
        df["stratum"] = "sin_ndvi"
    df = df[full.ravel()].copy()
    s2_date = pd.Timestamp(item.datetime.date())
    df.insert(0, "flight_dir", fdir)
    for k in ("year", "site", "crop", "stage"):
        df.insert(1, k, meta[k])
    df["date"], df["s2_date"] = meta.date.date(), s2_date.date()
    info = dict(flight_dir=fdir, year=meta.year, site=meta.site, crop=meta.crop, date=meta.date.date(),
                s2_id=item.id, s2_date=s2_date.date(), dt_days=(s2_date - meta.date).days, clear_frac=round(clear, 3),
                shift_dy_m=dy * 10, shift_dx_m=dx * 10, shift_r=round(best_r, 3), n_sectors=int(df.keep.sum()),
                n_sectors_full=len(df), status="OK")
    return df, info


def long_pairs(sec: pd.DataFrame) -> pd.DataFrame:
    out = []
    for b in BAND_ORDER:
        if f"dn_{b}" not in sec:
            continue
        d = sec[sec.keep & sec[f"dn_{b}"].notna() & (sec[f"rho_{b}"] > 0)]
        out.append(d[["year", "site", "crop", "flight_dir", "date", "stratum"]].assign(
            band=b, dn=d[f"dn_{b}"], rho=d[f"rho_{b}"]))
    return pd.concat(out, ignore_index=True)


def fit_pooled(pr: pd.DataFrame, min_n: int = 4) -> pd.DataFrame:  # noqa: C901
    """ρ = b(año, banda) + g(vuelo, banda)·DN sobre sectores; offset común = nivel de negro del sensor."""
    out = []
    for (year, band), g in pr.groupby(["year", "band"]):
        g = g.groupby("flight_dir").filter(lambda f: len(f) >= min_n)
        if g.flight_dir.nunique() < 2:
            continue
        flights = sorted(g.flight_dir.unique())
        idx = g.flight_dir.map({f: i for i, f in enumerate(flights)}).to_numpy()
        X = np.zeros((len(g), len(flights)))
        X[np.arange(len(g)), idx] = g.dn.to_numpy() / 65520.0
        y = g.rho.to_numpy()
        hub = HuberRegressor(epsilon=1.5, max_iter=5000, alpha=0.0).fit(X, y)
        pred = hub.predict(X)
        r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        for i, f in enumerate(flights):
            m = idx == i
            out.append(dict(year=year, band=band, flight_dir=f, date=g.loc[m, "date"].iloc[0],
                            site=g.loc[m, "site"].iloc[0], crop=g.loc[m, "crop"].iloc[0],
                            offset=hub.intercept_, gain=hub.coef_[i] / 65520.0, r2_pooled=r2,
                            rmse_flight=float(np.sqrt(((y[m] - pred[m]) ** 2).mean())), n_sectors=int(m.sum()),
                            rho_range_s2=float(np.ptp(y[m]))))
    res = pd.DataFrame(out).assign(method="M2")
    # M2b: vuelos con 1-3 sectores (campos pequeños, p. ej. garbanzo Fairfield 2019): offset fijo del año y banda,
    # ganancia por mínimos cuadrados con ese offset: g = Σ(ρ−b)·DN / ΣDN²
    extra = []
    for (f, band), g in pr.groupby(["flight_dir", "band"]):
        if ((res.flight_dir == f) & (res.band == band)).any() or len(g) < 1:
            continue
        yr = g.year.iloc[0]
        b = res[(res.year == yr) & (res.band == band)].offset
        if b.empty:
            continue
        b = float(b.iloc[0]); x, y = g.dn.to_numpy(), g.rho.to_numpy()
        gain = float(((y - b) * x).sum() / (x * x).sum())
        extra.append(dict(year=yr, band=band, flight_dir=f, date=g.date.iloc[0], site=g.site.iloc[0],
                          crop=g.crop.iloc[0], offset=b, gain=gain, r2_pooled=np.nan,
                          rmse_flight=float(np.sqrt(((y - (b + gain * x)) ** 2).mean())), n_sectors=len(g),
                          rho_range_s2=float(np.ptp(y)), method="M2b_offset_fijo"))
    return pd.concat([res, pd.DataFrame(extra)], ignore_index=True)


def fit_origin(pr: pd.DataFrame) -> pd.DataFrame:
    """M3: ρ = g(vuelo, banda)·DN, mínimos cuadrados por el origen sobre los sectores del vuelo.
    Evita el sesgo de atenuación del modelo con offset común (el rango de ρ dentro de un campo es estrecho y el DN es
    ruidoso, lo que aplasta la pendiente) y conserva el contraste relativo entre parcelas dentro del vuelo."""
    out = []
    for (f, band), g in pr.groupby(["flight_dir", "band"]):
        x, y = g.dn.to_numpy(), g.rho.to_numpy()
        gain = float((x * y).sum() / (x * x).sum())
        out.append(dict(year=g.year.iloc[0], band=band, flight_dir=f, date=g.date.iloc[0], site=g.site.iloc[0],
                        crop=g.crop.iloc[0], offset=0.0, gain=gain,
                        rmse_flight=float(np.sqrt(((y - gain * x) ** 2).mean())), n_sectors=len(g),
                        rho_range_s2=float(np.ptp(y)), method="M3_origen"))
    res = pd.DataFrame(out)
    for (yr, band), g in res.groupby(["year", "band"]):  # R² agrupado comparable con M2
        sub = pr[(pr.year == yr) & (pr.band == band)].merge(g[["flight_dir", "gain"]], on="flight_dir")
        pred = sub.gain * sub.dn
        res.loc[g.index, "r2_pooled"] = 1 - ((sub.rho - pred) ** 2).sum() / ((sub.rho - sub.rho.mean()) ** 2).sum()
    return res


def plaus_score(w: pd.DataFrame) -> pd.Series:
    """Puntaje de plausibilidad física por vuelo (menor = mejor): distancia a rangos esperados de dosel y suelo."""
    veg, soil = w[w.cls == "vegetation"].set_index("date"), w[w.cls == "soil"].set_index("date")
    pen = (veg.NDVI.clip(upper=0.85).rsub(0.85)                       # dosel: NDVI ≥ 0.85 en la mediana densa
           + (soil.NDVI - 0.25).clip(lower=0) + (0.05 - soil.NDVI).clip(lower=0)   # suelo: 0.05-0.25
           + (veg.red - 0.08).clip(lower=0) * 5)                       # dosel: rojo ≤ 0.08
    return pen


def fit_per_flight(pr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (f, band), g in pr.groupby(["flight_dir", "band"]):
        if len(g) < 4:
            continue
        x, y = g.dn.to_numpy(), g.rho.to_numpy()
        a, c = np.polyfit(x, y, 1)
        r2 = np.corrcoef(x, y)[0, 1] ** 2
        out.append(dict(flight_dir=f, band=band, gain_m1=a, offset_m1=c, r2_m1=r2, n=len(g),
                        strata=",".join(f"{k}:{v}" for k, v in g.stratum.value_counts().items())))
    return pd.DataFrame(out)


def plausibility(pooled: pd.DataFrame) -> pd.DataFrame:
    """Aplica los coeficientes a las medianas de dosel/suelo de la Fase 1c y verifica rangos físicos."""
    st = pd.read_csv(OUT / "03_spectral" / "spectral_stats.csv")
    key = (pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")[["flight_dir", "date", "year", "site", "crop"]]
           .drop_duplicates(["year", "site", "crop", "date"]))
    st = st.merge(key, on=["year", "site", "crop", "date"], how="left")
    st = st.merge(pooled[["flight_dir", "band", "offset", "gain"]], on=["flight_dir", "band"], how="inner")
    st["rho"] = st.offset + st.gain * st.p50 * 65520.0
    w = st.pivot_table(index=["year", "site", "crop", "date", "cls"], columns="band", values="rho").reset_index()
    if {"nir", "red"} <= set(w.columns):
        w["NDVI"] = (w.nir - w.red) / (w.nir + w.red)
    return w


def scatter_fig(pr: pd.DataFrame, pooled: pd.DataFrame, year: int):
    bands = [b for b in BAND_ORDER if b in pr.band.unique()]
    fig, axes = plt.subplots(1, len(bands), figsize=(2.3 * len(bands), 2.4), squeeze=False)
    for ax, b in zip(axes[0], bands):
        g = pr[(pr.year == year) & (pr.band == b)]
        co = pooled[(pooled.year == year) & (pooled.band == b)].set_index("flight_dir")
        if g.empty or co.empty:
            ax.set_axis_off(); continue
        g = g[g.flight_dir.isin(co.index)]
        pred = co.loc[g.flight_dir, "offset"].to_numpy() + co.loc[g.flight_dir, "gain"].to_numpy() * g.dn.to_numpy()
        for s, col in STRATA_COL.items():
            m = (g.stratum == s).to_numpy()
            ax.scatter(pred[m], g.rho.to_numpy()[m], s=7, color=col, alpha=0.7, lw=0, label=s)
        lim = [min(pred.min(), g.rho.min()), max(pred.max(), g.rho.max())]
        ax.plot(lim, lim, color=INK, lw=0.8)
        r2, rm = co.r2_pooled.iloc[0], np.sqrt(((g.rho.to_numpy() - pred) ** 2).mean())
        ax.text(0.04, 0.96, f"R²={r2:.2f}\nRMSE={rm:.3f}\nn={len(g)}", transform=ax.transAxes, va="top",
                fontsize=6, color=INK)
        ax.set_title(f"{b} → {S2_BAND[b]}", fontsize=7, color=INK)
        ax.set_xlabel("ρ UAV calibrada", fontsize=6); ax.tick_params(labelsize=6)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].set_ylabel("ρ Sentinel-2 L2A (sector 20 m)", fontsize=6)
    axes[0, -1].legend(fontsize=6, frameon=False, markerscale=1.5)
    fig.suptitle(f"Calibración UAV→S2 por sectores, {year} ({pooled.method.iloc[0]})", fontsize=7,
                 x=0.01, ha="left", color=INK)
    fig.savefig(OUTDIR / "scatter" / f"pooled_{year}.png", dpi=150, bbox_inches="tight"); plt.close(fig)


def main() -> None:
    (OUTDIR / "scatter").mkdir(parents=True, exist_ok=True)
    sec_path, info_path = OUTDIR / "sectors_uav_s2.csv.gz", OUTDIR / "flights_s2_match.csv"
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"].copy()
    inv["date"] = pd.to_datetime(inv["date"])
    secs = [pd.read_csv(sec_path)] if sec_path.exists() else []
    infos = pd.read_csv(info_path).to_dict("records") if info_path.exists() else []
    done = {i["flight_dir"] for i in infos}
    for fdir, g in inv.groupby("flight_dir"):
        if fdir in done:
            continue
        df, info = extract_flight(fdir, g)
        infos.append(info)
        if not df.empty:
            secs.append(df)
            pd.concat(secs, ignore_index=True).to_csv(sec_path, index=False)
        pd.DataFrame(infos).to_csv(info_path, index=False)
        print(f"{fdir}: {info.get('status')} S2={info.get('s2_date')} Δt={info.get('dt_days')} "
              f"desfase=({info.get('shift_dx_m')},{info.get('shift_dy_m')}) m r={info.get('shift_r')} "
              f"sectores={info.get('n_sectors')}/{info.get('n_sectors_full')}")

    sec = pd.concat(secs, ignore_index=True)
    pr = long_pairs(sec)
    m1 = fit_per_flight(pr)
    pooled = fit_pooled(pr).merge(m1, on=["flight_dir", "band"], how="left")
    origin = fit_origin(pr).merge(m1, on=["flight_dir", "band"], how="left")
    cand = {"M2": pooled, "M3": origin}
    plaus_all = []
    for name, co_ in cand.items():
        w = plausibility(co_).assign(model=name)
        plaus_all.append(w)
    plaus = pd.concat(plaus_all, ignore_index=True)
    plaus.to_csv(OUTDIR / "plausibility.csv", index=False)
    score = (plaus.groupby("model").apply(lambda w: plaus_score(w).median()))
    best = score.idxmin()
    print("Plausibilidad física (mediana de penalización, menor = mejor):", score.round(3).to_dict(), "→", best)
    pd.concat([c.assign(selected=(k == best)) for k, c in cand.items()], ignore_index=True).to_csv(
        OUTDIR / "calibration_candidates.csv", index=False)
    cand[best].to_csv(OUTDIR / "calibration_coefficients.csv", index=False)
    pooled = cand[best]
    for y in sorted(pr.year.unique()):
        scatter_fig(pr, pooled, y)

    info = pd.DataFrame(infos)
    with open(OUTDIR / "calibration_summary.md", "w", encoding="utf-8") as fh:
        fh.write("# Calibración cruzada UAV → Sentinel-2 L2A (muestreo por sectores de 20 m)\n\n")
        fh.write("## Emparejamiento de escenas y desfase\n\n" + info.to_markdown(index=False) + "\n\n")
        fh.write("## Sectores por estrato (válidos)\n\n"
                 + sec[sec.keep].groupby(["year", "stratum"]).size().unstack(fill_value=0).to_markdown() + "\n\n")
        fh.write("## M2 agrupado (offset común por año y banda) vs M1 por vuelo\n\n")
        fh.write(pooled.groupby(["year", "band"]).agg(offset=("offset", "first"), r2_pooled=("r2_pooled", "first"),
                                                      rmse_med=("rmse_flight", "median"),
                                                      r2_m1_med=("r2_m1", "median"),
                                                      n=("n_sectors", "sum")).round(4).to_markdown() + "\n\n")
        fh.write("## Plausibilidad física (medianas de dosel/suelo de la Fase 1c tras calibrar)\n\n")
        fh.write(plaus.round(3).to_markdown(index=False) + "\n")
    print(pooled.groupby(["year", "band"])[["offset", "r2_pooled", "rmse_flight"]].median().round(3))
    print(plaus.groupby(["model", "cls"])[["blue", "green", "red", "red edge", "nir", "NDVI"]].median().round(3))


if __name__ == "__main__":
    main()
