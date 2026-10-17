"""Paso 7b - ¿La calibración radiométrica permite predecir el rendimiento entre ambientes?

En el paso 15 los rasgos se estandarizan dentro de ambiente; eso elimina el nivel absoluto y hace imposible predecir
la media de un sitio-año nuevo (R² muy negativo en kg/ha con ambiente excluido). Aquí se comparan, con Random Forest
y XGBoost, tres versiones de los mismos rasgos en la grilla de GDD:
  (z)   estandarizados dentro de ambiente (como en el paso 15)
  (abs) reflectancia calibrada absoluta (calibración Sentinel-2, `05`): conserva diferencias entre ambientes
  (abs+z) ambos conjuntos
y se evalúa el rendimiento en kg/ha con dejar-un-ambiente-fuera y año futuro (2017-2018 → 2019).
Además, sin ninguna imagen: la media del rendimiento de entrenamiento (línea base nula, R² ≈ 0 o negativo).
Salida: outputs/15_models/{absolute_features.csv, fig_absolute_features.png}
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneGroupOut

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import CORE_FEATURES, gdd_grid, load, plot_table, zscore_within  # noqa: E402
from config import OUT  # noqa: E402

_spec = importlib.util.spec_from_file_location("mdl", Path(__file__).parent / "15_models.py")
mdl = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mdl)
OUTDIR = OUT / "15_models"


def main() -> None:
    d = load()
    pt = plot_table(d)
    G = gdd_grid(d, [f for f in CORE_FEATURES if f in d]).reindex(pt.index)
    G = G.loc[:, G.notna().mean() > 0.3]
    Z = G.apply(lambda c: zscore_within(c, pt.env))
    sets = {"z": Z, "abs": G, "abs+z": G.join(Z, rsuffix="_z")}
    rows = []
    for crop in ("pea", "chickpea"):
        idx = np.where((pt.crop == crop).to_numpy() & pt.seedyield.notna().to_numpy())[0]
        y, env, year = pt.seedyield.to_numpy(float), pt.env.to_numpy(), pt.year.to_numpy()
        splits = [("ambiente", tr, te) for tr, te in LeaveOneGroupOut().split(idx, groups=env[idx])]
        trf, tef = np.where(year[idx] < 2019)[0], np.where(year[idx] == 2019)[0]
        if len(trf) and len(tef):
            splits.append(("año futuro", trf, tef))
        for scheme, tr, te in splits:
            itr, ite = idx[tr], idx[te]
            base = np.full(len(ite), y[itr].mean())
            rows.append(dict(crop=crop, scheme=scheme, features="sin imágenes (media)", model="nulo",
                             test_env=",".join(sorted(set(env[ite]))), **mdl.metrics(y[ite], base, env[ite])))
            for name, X in sets.items():
                Xa = X.to_numpy(float)
                for mname in ("Random Forest", "XGBoost"):
                    m = mdl.sk_models()[mname].fit(Xa[itr], y[itr])
                    p = m.predict(Xa[ite])
                    rows.append(dict(crop=crop, scheme=scheme, features=name, model=mname,
                                     test_env=",".join(sorted(set(env[ite]))), **mdl.metrics(y[ite], p, env[ite])))
            print(f"{crop} {scheme} {sorted(set(env[ite]))}: " + ", ".join(
                f"{r['features']}/{r['model']} R²={r['r2']:.2f}" for r in rows[-7:]), flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(OUTDIR / "absolute_features.csv", index=False)
    s = R.groupby(["crop", "scheme", "features", "model"])[["r2", "rmse", "spearman"]].median().round(3)
    print(s.to_string())

    fig, axes = style.figure("2col", 2.8, ncols=2, sharey=True)
    order = ["sin imágenes (media)", "z", "abs", "abs+z"]
    for ax, crop, letter in zip(axes, ("pea", "chickpea"), "ab"):
        q = R[(R.crop == crop) & (R.scheme == "ambiente") & (R.model.isin(["nulo", "Random Forest"]))]
        data = [q[q.features == f].rmse.to_numpy() for f in order]
        bp = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=True)
        for patch, col in zip(bp["boxes"], [style.MUTED, style.CAT[0], style.CAT[1], style.CAT[2]]):
            patch.set(facecolor=col, alpha=0.5, edgecolor=style.MUTED)
        for med in bp["medians"]:
            med.set(color=style.INK)
        ax.set_xticks(range(1, 5)); ax.set_xticklabels(["media", "z", "abs", "abs+z"])
        ax.set_title(f"({letter}) {'Arveja' if crop == 'pea' else 'Garbanzo'}", loc="left")
    axes[0].set_ylabel("RMSE (kg/ha), dejar-un-ambiente-fuera")
    style.note(fig, "Random Forest con rasgos en la grilla de GDD: z = estandarizados dentro de ambiente; abs = "
                    "reflectancia calibrada absoluta (calibración Sentinel-2); media = sin imágenes. Cada caja resume "
                    "los ambientes de prueba (dejar-un-ambiente-fuera).")
    style.save(fig, OUTDIR / "fig_absolute_features")


if __name__ == "__main__":
    main()
