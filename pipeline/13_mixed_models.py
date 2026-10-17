"""Paso 6b (Fase 5) - Modelos mixtos: heredabilidad, correlaciones genéticas, coincidencia de selección y G×E.

Por ensayo (sitio-año × código de ensayo) y rasgo:
    y = μ + bloque + β1·fila + β2·fila² + β3·col + β4·col² + g + ε,   g ~ N(0, σ²g), ε ~ N(0, σ²e)
  - Fila/columna = posición de la parcela en el croquis (`06`); las tendencias polinómicas son una corrección espacial
    simple (la versión con P-splines bidimensionales, SpATS; Rodríguez-Álvarez et al. 2018, queda como extensión en R).
  - REML con statsmodels MixedLM.
  - H² en base a medias de genotipo = σ²g / (σ²g + σ²e / r), con r = repeticiones medias por genotipo (diseños casi
    balanceados; Holland et al. 2003). Para diseños desbalanceados se recomienda la H² de Cullis et al. (2006).
  - Valores genotípicos = μ + BLUP(g). Correlación con el rendimiento entre valores genotípicos (aproximación a la
    correlación genética; sesgada hacia cero por el encogimiento de los BLUP).
  - Coincidencia de selección: fracción del 20 % superior por rendimiento que también queda en el 20 % superior por
    el rasgo UAV (en la dirección de su correlación).
Rasgos: rendimiento y fenología/arquitectura; rasgos UAV de cada vuelo; parámetros de curva (`12`).
G×E: ensayos repetidos en ≥2 sitios del mismo año: y = ambiente + bloque(ambiente) + g + g×ambiente + ε (componentes
de varianza cruzados).
Salidas: outputs/13_mixed_models/{h2.csv, genotype_values.csv, genetic_corr_yield.csv, gxe.csv,
         fig_h2_by_gdd.png, fig_rg_yield_by_gdd.png}
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import load, plot_table  # noqa: E402
from config import OUT  # noqa: E402

warnings.filterwarnings("ignore")
OUTDIR = OUT / "13_mixed_models"
UAV = ["canopy_cover", "canopy_area_m2", "NDVI_mean", "NDRE_mean", "GNDVI_mean", "CIrededge_mean", "TVI_mean",
       "NDVI_sum", "MCARI_mean"]
FIELD = ["seedyield", "fiftyflowr", "physmatur", "canopyht", "vinelength"]
CURVE = ["x0", "max_rate", "auc", "ymax", "senescence_rate"]
UAV_ES = {"canopy_cover": "Cobertura", "canopy_area_m2": "Área de dosel", "NDVI_mean": "NDVI", "NDRE_mean": "NDRE",
          "GNDVI_mean": "GNDVI", "CIrededge_mean": "CIred-edge", "TVI_mean": "TVI", "NDVI_sum": "Suma NDVI",
          "MCARI_mean": "MCARI"}


def fit_trial(df: pd.DataFrame, y: str):
    d = df[[y, "entry_name", "block", "row", "col"]].dropna()
    if len(d) < 20 or d.entry_name.nunique() < 5 or d[y].std() == 0:
        return None
    d = d.assign(yz=(d[y] - d[y].mean()) / d[y].std(),
                 r=(d.row - d.row.mean()) / max(d.row.std(), 1e-6), c=(d.col - d.col.mean()) / max(d.col.std(), 1e-6))
    form = "yz ~ C(block) + r + I(r**2) + c + I(c**2)" if d.block.nunique() > 1 else "yz ~ r + I(r**2) + c + I(c**2)"
    try:
        m = smf.mixedlm(form, d, groups=d["entry_name"]).fit(reml=True, method=["lbfgs", "powell"])
    except Exception:
        return None
    vg = float(m.cov_re.iloc[0, 0]); ve = float(m.scale)
    reps = d.groupby("entry_name").size().mean()
    h2 = vg / (vg + ve / reps) if (vg + ve / reps) > 0 else np.nan
    blup = pd.Series({k: v.iloc[0] for k, v in m.random_effects.items()}) * d[y].std()
    gv = d[y].mean() + blup
    return dict(sigma_g=vg * d[y].var(), sigma_e=ve * d[y].var(), h2=h2, reps=reps, n=len(d),
                n_geno=d.entry_name.nunique()), gv


def coincidence(a: pd.Series, b: pd.Series, frac=0.2, sign=1.0) -> float:
    idx = a.index.intersection(b.index)
    if len(idx) < 10:
        return np.nan
    k = max(1, int(round(frac * len(idx))))
    ta = set(a.loc[idx].nlargest(k).index)
    tb = set((sign * b.loc[idx]).nlargest(k).index)
    return len(ta & tb) / k


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    d = load()
    pt = plot_table(d).reset_index()
    grid = gpd.read_file(OUT / "07_plot_grid" / "plot_grid_refined.gpkg", layer="plots")
    pos = grid[grid["kind"] == "plot"][["plot_uid", "map_row", "map_col"]].rename(columns={"map_row": "row",
                                                                                          "map_col": "col"})
    pt = pt.merge(pos, on="plot_uid", how="left")
    cp = pd.read_csv(OUT / "12_temporal" / "curve_params.csv")
    cpw = cp[cp.trait.isin(["canopy_cover", "NDVI_plotmean"])].pivot_table(index="plot_uid", columns="trait",
                                                                            values=CURVE)
    cpw.columns = [f"{t}:{p}" for p, t in cpw.columns]
    pt = pt.merge(cpw, left_on="plot_uid", right_index=True, how="left")

    h2rows, gvals, rg = [], [], []
    for (env, trial), g in pt.groupby(["env", "trial"]):
        mc = g.market_class.iloc[0]
        base = {}
        for t in FIELD + list(cpw.columns):
            if t in g and g[t].notna().sum() >= 20:
                r = fit_trial(g, t)
                if r:
                    h2rows.append(dict(env=env, trial=trial, market_class=mc, trait=t, flight_dir="", gdd=np.nan,
                                       **r[0]))
                    base[t] = r[1]
                    gvals.append(r[1].rename("value").to_frame().assign(env=env, trial=trial, trait=t, flight_dir=""))
        for f, gf in d[d.plot_uid.isin(g.plot_uid)].groupby("flight_dir"):
            gg = g.merge(gf[["plot_uid", "gdd"] + UAV], on="plot_uid")
            for t in UAV:
                r = fit_trial(gg, t)
                if not r:
                    continue
                gdd = float(gf.gdd.median())
                h2rows.append(dict(env=env, trial=trial, market_class=mc, trait=t, flight_dir=f, gdd=gdd, **r[0]))
                gvals.append(r[1].rename("value").to_frame().assign(env=env, trial=trial, trait=t, flight_dir=f))
                if "seedyield" in base:
                    a, b = base["seedyield"], r[1]
                    idx = a.index.intersection(b.index)
                    if len(idx) >= 10:
                        rgy = float(np.corrcoef(a.loc[idx], b.loc[idx])[0, 1])
                        rg.append(dict(env=env, trial=trial, market_class=mc, trait=t, flight_dir=f, gdd=gdd,
                                       r_geno_yield=rgy, coincidence_top20=coincidence(a, b, sign=np.sign(rgy)),
                                       n_geno=len(idx)))
        print(f"{env} {trial}: {sum(1 for h in h2rows if h['env'] == env and h['trial'] == trial)} modelos")
    h2 = pd.DataFrame(h2rows); h2.to_csv(OUTDIR / "h2.csv", index=False)
    pd.concat(gvals).rename_axis("entry_name").reset_index().to_csv(OUTDIR / "genotype_values.csv", index=False)
    rgd = pd.DataFrame(rg); rgd.to_csv(OUTDIR / "genetic_corr_yield.csv", index=False)
    gxe(pt, d)
    figures(h2, rgd)
    print(h2[h2.flight_dir == ""].groupby("trait").h2.median().round(2).to_string())


def gxe(pt: pd.DataFrame, d: pd.DataFrame) -> None:
    rows = []
    for (year, trial), g in pt.groupby(["year", "trial"]):
        if g.env.nunique() < 2:
            continue
        for t in ["seedyield"]:
            x = g[[t, "entry_name", "env", "block"]].dropna()
            if x.entry_name.nunique() < 5:
                continue
            x = x.assign(yz=(x[t] - x[t].mean()) / x[t].std(), one=1)
            try:
                m = smf.mixedlm("yz ~ C(env) + C(env):C(block)", x, groups="one",
                                vc_formula={"g": "0 + C(entry_name)", "ge": "0 + C(entry_name):C(env)"}).fit(reml=True)
                vc = dict(zip(m.model.exog_vc.names, m.vcomp))
                s2 = x[t].var()
                vg, vge, ve = vc.get("g", np.nan) * s2, vc.get("ge", np.nan) * s2, m.scale * s2
                ne = x.env.nunique(); r = x.groupby(["entry_name", "env"]).size().mean()
                rows.append(dict(year=year, trial=trial, trait=t, n_env=ne, sigma_g=vg, sigma_ge=vge, sigma_e=ve,
                                 ratio_ge_g=vge / vg if vg else np.nan,
                                 h2_multienv=vg / (vg + vge / ne + ve / (ne * r))))
            except Exception as e:  # noqa: BLE001
                rows.append(dict(year=year, trial=trial, trait=t, error=str(e)[:80]))
    pd.DataFrame(rows).to_csv(OUTDIR / "gxe.csv", index=False)


def binned(ax, q: pd.DataFrame, col: str, color, label, offset: float) -> None:
    """Mediana e IQR por intervalos de 200 GDD; solo intervalos con ≥3 ensayos (evita saltos por n pequeño)."""
    b = pd.cut(q.gdd, bins=np.arange(200, 1700, 200))
    agg = q.groupby(b, observed=True)[col].agg(["median", lambda v: v.quantile(0.25), lambda v: v.quantile(0.75),
                                                "count"])
    agg.columns = ["med", "q1", "q3", "n"]
    agg = agg[agg.n >= 3]
    if agg.empty:
        return
    x = np.array([iv.mid for iv in agg.index]) + offset
    ax.errorbar(x, agg.med, yerr=[agg.med - agg.q1, agg.q3 - agg.med], fmt="-o", ms=3.5, lw=1.2, capsize=1.5,
                color=color, label=label)


def figures(h2: pd.DataFrame, rg: pd.DataFrame) -> None:
    u = h2[h2.flight_dir != ""]
    fig, axes = style.figure("2col", 3.0, ncols=2, sharey=True)
    for ax, crop_classes, letter, title in ((axes[0], ["green_pea", "yellow_pea", "nz_green_yellow_pea"], "a", "Arveja"),
                                            (axes[1], ["kabuli_chickpea", "green_chickpea"], "b", "Garbanzo")):
        s = u[u.market_class.isin(crop_classes)]
        for i, t in enumerate(["canopy_cover", "NDVI_mean", "NDRE_mean", "CIrededge_mean"]):
            binned(ax, s[s.trait == t], "h2", style.CAT[i], UAV_ES[t], (i - 1.5) * 12)
        ax.set_xlabel("Grados-día del vuelo (°C·d)")
        ax.set_ylim(0, 1)
        ax.set_title(f"({letter}) {title}", loc="left")
    axes[0].set_ylabel("Heredabilidad (H², mediana entre ensayos)")
    axes[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    style.note(fig, "H² en base a medias de genotipo por ensayo (modelos mixtos con bloque y tendencias de fila/columna). "
                    "Mediana e intervalo intercuartílico por intervalos de 200 GDD; solo intervalos con ≥3 ensayos.")
    style.save(fig, OUTDIR / "fig_h2_by_gdd")
    if rg.empty:
        return
    fig, axes = style.figure("2col", 3.0, ncols=2, sharey=True)
    for ax, crop_classes, letter, title in ((axes[0], ["green_pea", "yellow_pea", "nz_green_yellow_pea"], "a", "Arveja"),
                                            (axes[1], ["kabuli_chickpea", "green_chickpea"], "b", "Garbanzo")):
        s = rg[rg.market_class.isin(crop_classes)]
        for i, t in enumerate(["canopy_cover", "NDVI_mean", "NDRE_mean", "CIrededge_mean"]):
            binned(ax, s[s.trait == t], "r_geno_yield", style.CAT[i], UAV_ES[t], (i - 1.5) * 12)
        ax.axhline(0, color=style.GRID, lw=0.8)
        ax.set_xlabel("Grados-día del vuelo (°C·d)")
        ax.set_title(f"({letter}) {title}", loc="left")
    axes[0].set_ylabel("Correlación entre valores genotípicos\ncon el rendimiento (mediana)")
    axes[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    style.save(fig, OUTDIR / "fig_rg_yield_by_gdd")


if __name__ == "__main__":
    main()
