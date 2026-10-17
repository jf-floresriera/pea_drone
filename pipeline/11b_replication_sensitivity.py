"""Paso 5b - Sensibilidad de la réplica: normalización en los conjuntos combinados por año.

Hipótesis: Zhang et al. (2021) normalizaron los datos "dentro de cada año y localidad (y dentro de los conjuntos
combinados de cada año)". Si en los conjuntos combinados la normalización se hizo sobre el conjunto agrupado y no dentro
de cada sitio, las diferencias de rendimiento ENTRE sitios permanecen en la variable objetivo y son fáciles de predecir
con imágenes (cada sitio difiere en vigor general), lo que inflaría el R² sin discriminar genotipos.
Se comparan, con el mismo LASSO del paso 11 (variantes original y anidada):
  (a) normalización dentro de sitio (paso 11)   (b) normalización sobre el conjunto agrupado del año.
Salida: outputs/11_replication/sensitivity_combined_normalization.csv y fig_sensitivity_normalization.png
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import REPL_FEATURES, gdd_grid, load, plot_table, zscore_within  # noqa: E402
from config import OUT  # noqa: E402

_spec = importlib.util.spec_from_file_location("rep", Path(__file__).parent / "11_replication.py")
rep = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rep)
OUTDIR = OUT / "11_replication"


def main() -> None:
    d = load()
    pt = plot_table(d)
    tasks = []
    for mc in rep.CLASSES:
        for year, g in d[d.market_class == mc].groupby("year"):
            if g.env.nunique() < 2:
                continue
            w0 = gdd_grid(g, REPL_FEATURES)
            y0 = pt.loc[w0.index, "seedyield"]
            ok = y0.notna(); w0, y0 = w0[ok], y0[ok]
            env = pt.loc[w0.index, "env"]
            cult = env + "|" + pt.loc[w0.index, "entry_name"]
            within = (w0.apply(lambda c: zscore_within(c, env)), zscore_within(y0, env))
            pooled = ((w0 - w0.mean()) / w0.std(ddof=0), (y0 - y0.mean()) / y0.std(ddof=0))
            for norm, (w, y) in (("dentro de sitio", within), ("conjunto agrupado", pooled)):
                for nested in (False, True):
                    tasks.append((mc, f"{year}_combinado", norm, "anidada" if nested else "original", w, y, cult, nested))

    def job(t):
        mc, ds, norm, var, w, y, cult, nested = t
        return dict(market_class=mc, dataset=ds, normalization=norm, variant=var, **rep.lasso_eval(w, y, cult, nested))
    rows = list(Parallel(n_jobs=min(12, len(tasks)))(delayed(job)(t) for t in tasks))
    res = pd.DataFrame(rows)
    res.to_csv(OUTDIR / "sensitivity_combined_normalization.csv", index=False)
    print(res.pivot_table(index=["market_class", "dataset", "variant"], columns="normalization",
                          values="r2_parcela").round(2).to_string())

    fig, ax = style.figure("1.5col", 3.0)
    s = res[res.variant == "original"]
    lab = (s.market_class.map(rep.CLASSES) + " " + s.dataset.str[:4]).unique()
    yk = {k: i for i, k in enumerate(sorted(lab))}
    for norm, col, off in (("dentro de sitio", style.CAT[0], -0.15), ("conjunto agrupado", style.CAT[1], 0.15)):
        q = s[s.normalization == norm]
        ax.scatter(q.r2_parcela, [yk[k] + off for k in q.market_class.map(rep.CLASSES) + " " + q.dataset.str[:4]],
                   color=col, s=24, label=f"Normalización {norm}", zorder=3)
    z = rep.ZHANG[rep.ZHANG.dataset.str.contains("combinado") & (rep.ZHANG.level == "parcela")]
    for _, r in z.iterrows():
        k = rep.CLASSES[r.market_class] + " " + r.dataset[:4]
        if k in yk:
            ax.scatter(r.r2_zhang, yk[k], marker="|", s=140, color=style.INK, label="Zhang et al. (2021)")
    h, l_ = ax.get_legend_handles_labels()
    uniq = dict(zip(l_, h))
    ax.legend(uniq.values(), uniq.keys(), loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set_yticks(range(len(yk))); ax.set_yticklabels(list(yk))
    ax.set_xlabel("R² de prueba (LASSO, nivel parcela, conjuntos combinados por año)")
    ax.axvline(0, color=style.GRID, lw=0.8)
    ax.set_title("Efecto de la normalización en los conjuntos combinados")
    style.save(fig, OUTDIR / "fig_sensitivity_normalization")


if __name__ == "__main__":
    main()
