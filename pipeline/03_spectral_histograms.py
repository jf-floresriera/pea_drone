"""Fase 1c - Respuesta espectral exploratoria de los ortomosaicos (antes de calibrar).

Por vuelo con 5 bandas: lectura submuestreada, separación vegetación/suelo por umbral de Otsu
sobre NDVI calculado con DN, histogramas por banda y firma espectral (mediana e IQR) por clase.
Objetivo: documentar el estado radiométrico de partida (DN sin calibrar, 12 bit × 16) y mostrar
la variación entre fechas que justifica la calibración de la Fase 2.
Salidas: outputs/03_spectral/{spectral_stats.csv, hist_<grupo>.png, signature_<grupo>.png, quicklook/}
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import BAND_ORDER, BANDS, OUT  # noqa: E402

DECIM = 6
DN_MAX = 65520.0  # 4095 × 16: rango de la RedEdge (12 bit) almacenado en 16 bit
OUTDIR = OUT / "03_spectral"
VEG, SOIL, INK, MUTED = "#1baf7a", "#eb6834", "#0b0b0b", "#52514e"
BINS = np.linspace(0, 1, 101)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def otsu(x: np.ndarray, nbins: int = 256) -> float:
    hist, edges = np.histogram(x, bins=nbins)
    mids = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist); w1 = w0[-1] - w0
    m0 = np.cumsum(hist * mids) / np.maximum(w0, 1)
    m1 = (np.sum(hist * mids) - np.cumsum(hist * mids)) / np.maximum(w1, 1)
    return float(mids[np.argmax(w0 * w1 * (m0 - m1) ** 2)])


def read_flight(paths: dict[str, Path]):
    arrs, alpha = {}, None
    for b in BAND_ORDER:
        with rasterio.open(paths[b]) as r:
            d = r.read(out_shape=(r.count, r.height // DECIM, r.width // DECIM), resampling=Resampling.nearest)
        arrs[b] = d[0].astype(np.float32) / DN_MAX
        a = d[-1] > 0 if r.count > 1 else d[0] > 0  # sin alfa: DN = 0 como fuera de mosaico
        alpha = a if alpha is None else alpha & a
    return arrs, alpha


def quicklook(arrs, alpha, dest: Path, title: str):
    def stretch(a):
        lo, hi = np.percentile(a[alpha], [2, 98])
        return np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)
    cir = np.dstack([stretch(arrs["nir"]), stretch(arrs["red"]), stretch(arrs["green"])])
    cir[~alpha] = 1
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow(cir); ax.set_axis_off(); ax.set_title(title, color=INK, fontsize=8)
    fig.savefig(dest); plt.close(fig)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "quicklook").mkdir(exist_ok=True)
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"]
    complete = inv.groupby("flight_dir").filter(lambda g: g.band.nunique() == 5)

    stats, hists = [], {}
    for (year, site, crop, stage, date, fdir), g in complete.groupby(
            ["year", "site", "crop", "stage", "date", "flight_dir"], dropna=False):
        paths = {r.band: Path(OUT.parent / r.path) for r in g.itertuples()}
        arrs, alpha = read_flight(paths)
        ndvi = (arrs["nir"] - arrs["red"]) / (arrs["nir"] + arrs["red"] + 1e-6)
        thr = otsu(ndvi[alpha])
        cls = {"vegetation": alpha & (ndvi > thr), "soil": alpha & (ndvi <= thr)}
        group = f"{year}_{site}_{crop}{'_' + stage if isinstance(stage, str) and stage else ''}"
        print(f"{group} {date}: Otsu NDVI_DN={thr:.3f}, veg={cls['vegetation'].sum() / alpha.sum():.1%}")
        for c, m in cls.items():
            for b in BAND_ORDER:
                v = arrs[b][m]
                q = np.percentile(v, [5, 25, 50, 75, 95])
                stats.append(dict(group=group, year=year, site=site, crop=crop, date=date, cls=c, band=b,
                                  wavelength_nm=BANDS[b][0], n_px=int(m.sum()), frac=m.sum() / alpha.sum(),
                                  ndvi_dn_otsu=thr, p5=q[0], p25=q[1], p50=q[2], p75=q[3], p95=q[4],
                                  mean=v.mean(), std=v.std()))
                hists[(group, date, c, b)] = np.histogram(v, BINS, density=True)[0]
        quicklook(arrs, alpha, OUTDIR / "quicklook" / f"{group}_{date}.png", f"{group} {date} (CIR)")

    st = pd.DataFrame(stats)
    st.to_csv(OUTDIR / "spectral_stats.csv", index=False)

    mids = (BINS[:-1] + BINS[1:]) / 2
    for group, gs in st.groupby("group"):
        dates = sorted(gs.date.unique())
        # (a) Histogramas: filas = fechas, columnas = bandas
        fig, axes = plt.subplots(len(dates), 5, figsize=(10, 1.5 * len(dates) + 0.6), sharex=True, squeeze=False)
        for i, d in enumerate(dates):
            for j, b in enumerate(BAND_ORDER):
                ax = axes[i, j]
                for c, col in (("soil", SOIL), ("vegetation", VEG)):
                    h = hists[(group, d, c, b)]
                    ax.fill_between(mids, h, color=col, alpha=0.25, lw=0)
                    ax.plot(mids, h, color=col, lw=1.2, label=c if (i == 0 and j == 0) else None)
                ax.set_yticks([])
                if i == 0:
                    ax.set_title(f"{b} ({BANDS[b][0]} nm)", color=INK)
                if j == 0:
                    ax.set_ylabel(d, rotation=0, ha="right", va="center", color=INK)
                if i == len(dates) - 1:
                    ax.set_xlabel("DN / 65520")
        fig.legend(loc="upper right", frameon=False, ncol=2, labels=["suelo", "vegetación"],
                   handles=[plt.Line2D([], [], color=SOIL, lw=2), plt.Line2D([], [], color=VEG, lw=2)])
        fig.suptitle(f"Histogramas por banda (DN sin calibrar) — {group}", x=0.01, ha="left", color=INK)
        fig.savefig(OUTDIR / f"hist_{group}.png"); plt.close(fig)

        # (b) Firma espectral por fecha: un panel por clase, fechas en rampa de un solo tono
        ramp = plt.cm.Blues(np.linspace(0.35, 0.95, len(dates)))
        fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=True)
        for ax, c in zip(axes, ("vegetation", "soil")):
            for d, col in zip(dates, ramp):
                s = gs[(gs.cls == c) & (gs.date == d)].sort_values("wavelength_nm")
                ax.fill_between(s.wavelength_nm, s.p25, s.p75, color=col, alpha=0.15, lw=0)
                ax.plot(s.wavelength_nm, s.p50, "-o", color=col, lw=2, ms=4, label=d)
            ax.set_title({"vegetation": "Vegetación", "soil": "Suelo"}[c], color=INK, loc="left")
            ax.set_xlabel("Longitud de onda (nm)")
            ax.set_xticks([BANDS[b][0] for b in BAND_ORDER])
        axes[0].set_ylabel("DN / 65520 (mediana, IQR)")
        axes[1].legend(frameon=False, fontsize=7, title="Fecha", title_fontsize=7)
        fig.suptitle(f"Firma espectral sin calibrar — {group}", x=0.01, ha="left", color=INK)
        fig.savefig(OUTDIR / f"signature_{group}.png"); plt.close(fig)


if __name__ == "__main__":
    main()
