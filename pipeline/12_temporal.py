"""Paso 6a (Fase 5) - Dinámica temporal del dosel en función de grados-día (GDD).

Para cada parcela y rasgo (cobertura del dosel, NDVI, NDRE, GNDVI, CIrededge):
  - Logística de 3 parámetros sobre la fase creciente (hasta el máximo observado + 1 fecha):
        y(GDD) = A / (1 + exp(−k·(GDD − x0)))
    A = máximo asintótico, k = tasa, x0 = GDD de inflexión (≈ momento de máximo crecimiento).
    Se ajusta con scipy.optimize.curve_fit con límites físicos; si no converge o hay < 3 puntos, se usan solo los
    descriptores empíricos.
  - Descriptores empíricos: máximo observado, GDD del máximo, AUC (trapecio sobre la grilla común 400-1150 GDD,
    interpolada) y tasa de senescencia = pendiente entre el máximo y la última fecha (si el máximo no es la última).
Inspirado en Borra-Serrano et al. (2020), que ajustaron funciones sigmoides a series UAV de cobertura y altura.
Salidas: outputs/12_temporal/{curve_params.csv, fig_curves_by_class.png, fig_param_distributions.png}
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import OptimizeWarning, curve_fit

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import GDD_GRID, load, plot_table  # noqa: E402
from config import OUT  # noqa: E402

warnings.filterwarnings("ignore", category=OptimizeWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
OUTDIR = OUT / "12_temporal"
CURVE_TRAITS = {"canopy_cover": "Cobertura del dosel", "NDVI_plotmean": "NDVI (parcela)",
                "NDRE_plotmean": "NDRE (parcela)", "GNDVI_plotmean": "GNDVI (parcela)",
                "CIrededge_plotmean": "CIred-edge (parcela)"}


def logistic(x, A, k, x0):
    return A / (1 + np.exp(-k * (x - x0)))


def fit_plot(x: np.ndarray, y: np.ndarray) -> dict:
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    out = dict(n_dates=len(x))
    if len(x) < 2:
        return out
    o = np.argsort(x); x, y = x[o], y[o]
    imax = int(np.argmax(y))
    out.update(ymax=float(y[imax]), gdd_at_max=float(x[imax]))
    if imax < len(x) - 1:
        out["senescence_rate"] = float((y[-1] - y[imax]) / (x[-1] - x[imax]) * 100)  # por 100 GDD
    xi = np.interp(GDD_GRID, x, y, left=np.nan, right=np.nan)
    if np.isfinite(xi).sum() >= 2:
        g = GDD_GRID[np.isfinite(xi)]; v = xi[np.isfinite(xi)]
        out["auc"] = float(np.trapezoid(v, g) / (g[-1] - g[0]))  # media integrada en el rango común
        out["auc_range"] = f"{g[0]}-{g[-1]}"
    xs, ys = x[:imax + 2], y[:imax + 2]
    if len(xs) >= 3 and np.ptp(ys) > 0:
        lo = [max(ys.max() * 0.8, 1e-6), 1e-4, 0]
        hi = [max(ys.max() * 1.5, lo[0] * 1.01), 0.1, 2500]
        p0 = [min(max(ys.max(), lo[0] * 1.01), hi[0] * 0.99), 0.01, float(np.median(xs))]
        try:
            p, _ = curve_fit(logistic, xs, ys, p0=p0, bounds=(lo, hi), maxfev=5000)
            pred = logistic(xs, *p)
            ss = ((ys - ys.mean()) ** 2).sum()
            out.update(A=p[0], k=p[1], x0=p[2], logistic_r2=float(1 - ((ys - pred) ** 2).sum() / ss) if ss else np.nan,
                       max_rate=float(p[0] * p[1] / 4 * 100))  # pendiente máxima por 100 GDD
        except (RuntimeError, ValueError):
            pass
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    d = load()
    pt = plot_table(d)
    rows = []
    for uid, g in d.groupby("plot_uid"):
        for t in CURVE_TRAITS:
            if t not in g:
                continue
            r = fit_plot(g.gdd.to_numpy(float), g[t].to_numpy(float))
            rows.append(dict(plot_uid=uid, trait=t, **r))
    cp = pd.DataFrame(rows).merge(pt.reset_index()[["plot_uid", "env", "market_class", "entry_name"]], on="plot_uid")
    cp.to_csv(OUTDIR / "curve_params.csv", index=False)
    print(cp.groupby("trait")[["n_dates", "logistic_r2", "x0", "max_rate", "auc"]].median().round(3).to_string())
    print("ajustes logísticos válidos:", cp.dropna(subset=["A"]).groupby("trait").size().to_dict())

    # Fig. curvas medias por clase comercial (cobertura y NDVI) con banda intercuartílica
    fig, axes = style.figure("2col", 2.8, ncols=2)
    for ax, t, letter in zip(axes, ("canopy_cover", "NDVI_plotmean"), "ab"):
        for mc, col in style.MARKET.items():
            g = d[d.market_class == mc]
            if g.empty:
                continue
            b = pd.cut(g.gdd, bins=np.arange(200, 1700, 150))
            s = g.groupby(b, observed=True)[t].quantile([0.25, 0.5, 0.75]).unstack()
            mid = [iv.mid for iv in s.index]
            ax.fill_between(mid, s[0.25], s[0.75], color=col, alpha=0.15, lw=0)
            ax.plot(mid, s[0.5], color=col, label=style.MARKET_ES[mc], marker="o", ms=3)
        ax.axvspan(721, 772, color=style.GRID, zorder=0)
        ax.set_xlabel("Grados-día desde la siembra (°C·d, base 3 °C)")
        ax.set_ylabel(CURVE_TRAITS[t])
        style.panel_label(ax, letter)
    axes[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    style.note(fig, "Mediana y rango intercuartílico por intervalos de 150 GDD, todas las parcelas y ambientes. "
                    "Franja gris: floración (721-772 GDD; Zhang et al., 2021).")
    style.save(fig, OUTDIR / "fig_curves_by_class")

    # Fig. distribuciones de parámetros (cobertura) por clase
    c = cp[cp.trait == "canopy_cover"]
    params = [("x0", "GDD de inflexión"), ("max_rate", "Tasa máx. (/100 GDD)"), ("auc", "AUC media"),
              ("senescence_rate", "Senescencia (/100 GDD)")]
    fig, axes = style.figure("2col", 2.4, ncols=4)
    for ax, (p, lab), letter in zip(axes, params, "abcd"):
        data = [c[c.market_class == mc][p].dropna() for mc in style.MARKET]
        labels = [style.wrap(style.MARKET_ES[mc], 10) for mc in style.MARKET]
        bp = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=False)
        for patch, col in zip(bp["boxes"], style.MARKET.values()):
            patch.set(facecolor=col, alpha=0.6, edgecolor=style.MUTED)
        for med in bp["medians"]:
            med.set(color=style.INK)
        ax.set_xticks(range(1, len(labels) + 1)); ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=6)
        ax.set_ylabel(lab)
        style.panel_label(ax, letter)
    style.note(fig, "Parámetros de la curva de cobertura del dosel por parcela (logística sobre la fase creciente).")
    style.save(fig, OUTDIR / "fig_param_distributions")


if __name__ == "__main__":
    main()
