"""Paso 6c (Fase 5) - Fenología desde el aire.

Objetivo: estimar días a 50 % de floración (`fiftyflowr`) y a madurez fisiológica (`physmatur`) a partir de la
dinámica del dosel, en los ambientes con fenología registrada (Pullman 2017-2019; Fairfield 2017 tal como se entregó).
1. Lo observado se expresa también en GDD (tabla diaria de `08`) para comparar con la escala de los parámetros de curva.
2. Correlaciones de Pearson entre la fenología observada y los parámetros de curva (`12`: x0, GDD del máximo,
   tasa máxima, senescencia, AUC) y los rasgos interpolados a la grilla de GDD.
3. Modelo predictivo: regresión ridge (RidgeCV) sobre parámetros de curva + rasgos en la grilla de GDD, con
   validación GroupKFold por genotipo (5 particiones) y estandarización dentro de ambiente.
   Métricas: R², RMSE (días) y ρ de Spearman.
Salidas: outputs/14_phenology/{phenology_correlations.csv, phenology_cv.csv, fig_phenology_obs_pred.png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import CORE_FEATURES, gdd_grid, load, plot_table, zscore_within  # noqa: E402
from config import OUT  # noqa: E402

OUTDIR = OUT / "14_phenology"
PHENO = {"fiftyflowr": "Días a 50 % de floración", "physmatur": "Días a madurez fisiológica"}


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    d = load()
    pt = plot_table(d)
    gdd = pd.read_csv(OUT / "08_weather" / "gdd_by_trial_day.csv", dtype={"trial": str})
    for t in PHENO:  # fenología observada en GDD
        m = pt[["trial", "year", "site", t]].reset_index().merge(
            gdd[["year", "site", "trial", "das", "gdd_cum"]], left_on=["year", "site", "trial", t],
            right_on=["year", "site", "trial", "das"], how="left").set_index("plot_uid")
        pt[f"{t}_gdd"] = m.gdd_cum
    cp = pd.read_csv(OUT / "12_temporal" / "curve_params.csv")
    cpw = cp[cp.trait.isin(["canopy_cover", "NDVI_plotmean", "NDRE_plotmean"])].pivot_table(
        index="plot_uid", columns="trait", values=["x0", "gdd_at_max", "max_rate", "senescence_rate", "auc", "ymax"])
    cpw.columns = [f"{t}:{p}" for p, t in cpw.columns]
    grid = gdd_grid(d, [f for f in CORE_FEATURES if f in d])
    X_all = cpw.join(grid, how="outer")

    cors, cvs, preds = [], [], []
    for crop, gcrop in pt.groupby("crop"):
        for t in PHENO:
            y = gcrop[t].dropna()
            if len(y) < 40:
                continue
            X = X_all.reindex(y.index)
            for c in cpw.columns:
                x = X[c]; ok = x.notna()
                if ok.sum() >= 30 and x[ok].std() > 0:
                    r, p = pearsonr(x[ok], y[ok])
                    cors.append(dict(crop=crop, target=t, feature=c, r=r, p=p, n=int(ok.sum())))
            env = gcrop.loc[y.index, "env"]
            Xz = X.loc[:, X.notna().mean() > 0.6].apply(lambda c: zscore_within(c, env))
            groups = gcrop.loc[y.index, "entry_name"]
            model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                  RidgeCV(alphas=np.logspace(-2, 3, 30)))
            pred = pd.Series(np.nan, index=y.index)
            for tr, te in GroupKFold(n_splits=5).split(Xz, y, groups):
                model.fit(Xz.iloc[tr], y.iloc[tr])
                pred.iloc[te] = model.predict(Xz.iloc[te])
            cvs.append(dict(crop=crop, target=t, n=len(y), n_features=Xz.shape[1], r2=r2_score(y, pred),
                            rmse_days=float(np.sqrt(mean_squared_error(y, pred))), spearman=spearmanr(y, pred)[0]))
            preds.append(pd.DataFrame(dict(obs=y, pred=pred, crop=crop, target=t, env=env)))
            print(f"{crop} {t}: R²={cvs[-1]['r2']:.2f} RMSE={cvs[-1]['rmse_days']:.1f} d n={len(y)}")
    pd.DataFrame(cors).to_csv(OUTDIR / "phenology_correlations.csv", index=False)
    pd.DataFrame(cvs).to_csv(OUTDIR / "phenology_cv.csv", index=False)
    pr = pd.concat(preds) if preds else pd.DataFrame()
    pr.to_csv(OUTDIR / "phenology_predictions.csv")

    if pr.empty:
        return
    combos = pr[["crop", "target"]].drop_duplicates().to_numpy()
    fig, axes = style.figure("2col", 2.6, ncols=len(combos), squeeze=False)
    for ax, (crop, t), letter in zip(axes[0], combos, "abcd"):
        s = pr[(pr.crop == crop) & (pr.target == t)]
        for i, (env, e) in enumerate(s.groupby("env")):
            ax.scatter(e.obs, e.pred, s=8, alpha=0.6, color=style.CAT[i % 8], label=env.replace("_", " "), lw=0)
        lim = [min(s.obs.min(), s.pred.min()) - 1, max(s.obs.max(), s.pred.max()) + 1]
        ax.plot(lim, lim, color=style.INK, lw=0.8)
        c = [x for x in cvs if x["crop"] == crop and x["target"] == t][0]
        ax.text(0.03, 0.97, f"R² = {c['r2']:.2f}\nRMSE = {c['rmse_days']:.1f} d", transform=ax.transAxes,
                va="top", fontsize=6.5)
        ax.set_xlabel("Observado (días)"); ax.set_ylabel("Predicho (días)")
        ax.set_title(f"({letter}) {'Arveja' if crop == 'pea' else 'Garbanzo'}: {style.wrap(PHENO[t], 22)}", loc="left")
    axes[0][-1].legend(loc="upper left", bbox_to_anchor=(1.02, 1), markerscale=2)
    style.note(fig, "Predicción por validación cruzada agrupada por genotipo (5 particiones); ridge sobre parámetros de "
                    "curva y rasgos en la grilla de grados-día, estandarizados dentro de ambiente.")
    style.save(fig, OUTDIR / "fig_phenology_obs_pred")


if __name__ == "__main__":
    main()
