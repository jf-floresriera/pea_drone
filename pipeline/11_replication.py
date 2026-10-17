"""Paso 5 (Fase 4) - Réplica de Zhang et al. (2021).

A) Correlaciones de Pearson entre rasgos UAV (área de dosel; media y suma de NDVI, GNDVI, SAVI, NDRE, TVI) de cada vuelo
   y (i) rendimiento, (ii) días a 50 % de floración y (iii) días a madurez fisiológica, por sitio-año y clase
   comercial, a nivel de parcela y de cultivar (media de las repeticiones).
B) LASSO para rendimiento, con la configuración del artículo:
   - rasgos y rendimiento estandarizados dentro de sitio-año;
   - selección: LASSO con CV de 5 particiones repetida 3 veces; se retienen los rasgos seleccionados en ≥75 % de
     los ajustes;
   - evaluación a nivel de parcela: 4 particiones aleatorias 3:1 (R² de prueba);
   - evaluación a nivel de cultivar: dejar-un-cultivar-fuera (LOO).
   Variantes: "original" (selección con todos los datos, como en el artículo) y "anidada" (selección repetida solo
   con los datos de entrenamiento de cada partición, sin fuga de información).
   Conjuntos: cada sitio-año y la combinación de sitios dentro de cada año (grilla común de GDD).
Salidas: outputs/11_replication/{correlations.csv, max_correlations.csv, lasso_results.csv,
         comparison_zhang2021.csv, fig_correlations_*.png, fig_lasso_vs_zhang.png}
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LassoCV
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut, RepeatedKFold, ShuffleSplit

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import REPL_FEATURES, gdd_grid, load, plot_table, wide_by_flight, zscore_within  # noqa: E402
from config import OUT  # noqa: E402

warnings.filterwarnings("ignore", category=ConvergenceWarning)
OUTDIR = OUT / "11_replication"
CLASSES = {"kabuli_chickpea": "Garbanzo kabuli", "green_pea": "Arveja verde", "yellow_pea": "Arveja amarilla"}
TARGETS = {"seedyield": "Rendimiento", "fiftyflowr": "Días a floración", "physmatur": "Días a madurez"}
# Valores publicados (Zhang et al. 2021, LASSO, R² de prueba)
ZHANG = pd.DataFrame([
    ("kabuli_chickpea", "2017_Pullman", "parcela", 0.32), ("kabuli_chickpea", "2018_Pullman", "parcela", 0.53),
    ("kabuli_chickpea", "2018_Genesee", "parcela", 0.33), ("kabuli_chickpea", "2019_Pullman", "parcela", 0.57),
    ("kabuli_chickpea", "2019_Genesee", "parcela", 0.51), ("kabuli_chickpea", "2019_Fairfield", "parcela", 0.70),
    ("kabuli_chickpea", "2018_combinado", "parcela", 0.89), ("kabuli_chickpea", "2019_combinado", "parcela", 0.82),
    ("kabuli_chickpea", "2018_combinado", "cultivar", 0.91), ("kabuli_chickpea", "2019_combinado", "cultivar", 0.76),
], columns=["market_class", "dataset", "level", "r2_zhang"])


def correlations(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (env, mc, f), g in d[d.market_class.isin(CLASSES)].groupby(["env", "market_class", "flight_dir"]):
        gdd = g.gdd.median()
        cult = g.groupby("entry_name")[REPL_FEATURES + list(TARGETS)].mean()
        for t in TARGETS:
            for level, data in (("parcela", g), ("cultivar", cult)):
                y = data[t]
                if y.notna().sum() < 10 or y.std() == 0:
                    continue
                for feat in REPL_FEATURES:
                    x = data[feat]
                    ok = x.notna() & y.notna()
                    if ok.sum() < 10 or x[ok].std() == 0:
                        continue
                    r, p = pearsonr(x[ok], y[ok])
                    rows.append(dict(env=env, market_class=mc, flight_dir=f, gdd=gdd, target=t, level=level,
                                     feature=feat, r=r, p=p, n=int(ok.sum())))
    return pd.DataFrame(rows)


def select_features(X: np.ndarray, y: np.ndarray, seed: int = 0) -> np.ndarray:
    """Frecuencia de selección de LASSO en CV 5×3; devuelve la máscara de rasgos con frecuencia ≥ 0,75."""
    rkf = RepeatedKFold(n_splits=5, n_repeats=3, random_state=seed)
    counts = np.zeros(X.shape[1])
    n = 0
    for tr, _ in rkf.split(X):
        m = LassoCV(cv=5, random_state=seed, n_alphas=50, max_iter=5000).fit(X[tr], y[tr])
        counts += m.coef_ != 0
        n += 1
    return counts / n >= 0.75


def lasso_eval(X: pd.DataFrame, y: pd.Series, cultivar: pd.Series, nested: bool, seed: int = 0) -> dict:
    X = X.loc[:, X.notna().mean() > 0.7]
    X = X.fillna(X.median())
    X = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
    Xa, ya = X.to_numpy(), y.to_numpy()
    sel_all = select_features(Xa, ya, seed) if not nested else None
    r2s, nsel = [], []
    for tr, te in ShuffleSplit(n_splits=4, test_size=0.25, random_state=seed).split(Xa):
        sel = select_features(Xa[tr], ya[tr], seed) if nested else sel_all
        nsel.append(int(sel.sum()))
        if sel.sum() == 0:
            r2s.append(np.nan)
            continue
        m = LassoCV(cv=5, random_state=seed, n_alphas=50, max_iter=5000).fit(Xa[tr][:, sel], ya[tr])
        r2s.append(r2_score(ya[te], m.predict(Xa[te][:, sel])))
    # Nivel cultivar: LOO sobre medias de cultivar
    Xc = X.groupby(cultivar.values).mean(); yc = y.groupby(cultivar.values).mean()
    Xc_, yc_ = Xc.to_numpy(), yc.to_numpy()
    selc = select_features(Xc_, yc_, seed) if not nested else None
    pred = np.full(len(yc_), np.nan)
    for tr, te in LeaveOneOut().split(Xc_):
        s = selc if not nested else select_features(Xc_[tr], yc_[tr], seed)
        if s.sum() == 0:
            continue
        m = LassoCV(cv=5, random_state=seed, n_alphas=50, max_iter=5000).fit(Xc_[tr][:, s], yc_[tr])
        pred[te] = m.predict(Xc_[te][:, s])
    ok = np.isfinite(pred)
    r2c = r2_score(yc_[ok], pred[ok]) if ok.sum() > 5 else np.nan
    return dict(r2_parcela=np.nanmean(r2s) if np.isfinite(r2s).any() else np.nan,
                r2_parcela_sd=np.nanstd(r2s) if np.isfinite(r2s).any() else np.nan,
                n_selected=float(np.mean(nsel)), r2_cultivar=r2c, n_plots=len(ya), n_cultivars=len(yc_),
                n_features=X.shape[1])


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    d = load()
    pt = plot_table(d)
    cor = correlations(d)
    cor.to_csv(OUTDIR / "correlations.csv", index=False)
    mx = (cor.assign(absr=cor.r.abs()).sort_values("absr", ascending=False)
          .groupby(["market_class", "target", "level"]).head(1))
    mx.to_csv(OUTDIR / "max_correlations.csv", index=False)
    print(mx[["market_class", "target", "level", "env", "feature", "r", "n"]].round(3).to_string())

    rows = []
    for mc in CLASSES:
        sub = d[d.market_class == mc]
        # (a) cada sitio-año con rasgos por vuelo
        for env, g in sub.groupby("env"):
            w = wide_by_flight(g, REPL_FEATURES)
            y = pt.loc[w.index, "seedyield"]
            ok = y.notna()
            if ok.sum() < 30:
                continue
            w, y = w[ok], zscore_within(y[ok], pt.loc[w.index[ok], "env"])
            for nested in (False, True):
                r = lasso_eval(w, y, pt.loc[w.index, "entry_name"], nested)
                rows.append(dict(market_class=mc, dataset=env, variant="anidada" if nested else "original", **r))
                print(f"{mc} {env} {'anidada' if nested else 'original'}: R²parcela={r['r2_parcela']:.2f} "
                      f"R²cultivar={r['r2_cultivar']:.2f} sel={r['n_selected']:.1f}")
        # (b) combinado dentro de año (grilla de GDD, estandarizado dentro de sitio)
        for year, g in sub.groupby("year"):
            if g.env.nunique() < 2:
                continue
            w = gdd_grid(g, REPL_FEATURES)
            w = w.apply(lambda c: zscore_within(c, pt.loc[w.index, "env"]))
            y = pt.loc[w.index, "seedyield"]
            ok = y.notna()
            w, y = w[ok], zscore_within(y[ok], pt.loc[w.index[ok], "env"])
            cult = pt.loc[w.index, "env"] + "|" + pt.loc[w.index, "entry_name"]
            for nested in (False, True):
                r = lasso_eval(w, y, cult, nested)
                rows.append(dict(market_class=mc, dataset=f"{year}_combinado", variant="anidada" if nested else "original",
                                 **r))
                print(f"{mc} {year} combinado {'anidada' if nested else 'original'}: R²parcela={r['r2_parcela']:.2f} "
                      f"R²cultivar={r['r2_cultivar']:.2f}")
    las = pd.DataFrame(rows)
    las.to_csv(OUTDIR / "lasso_results.csv", index=False)
    long = las.melt(id_vars=["market_class", "dataset", "variant"], value_vars=["r2_parcela", "r2_cultivar"],
                    var_name="level", value_name="r2")
    long["level"] = long.level.str.replace("r2_", "")
    comp = ZHANG.merge(long, on=["market_class", "dataset", "level"], how="left")
    comp.to_csv(OUTDIR / "comparison_zhang2021.csv", index=False)
    figures(cor, comp)


def figures(cor: pd.DataFrame, comp: pd.DataFrame) -> None:
    # Fig. correlaciones con rendimiento (nivel parcela): filas = sitio-año × vuelo (por GDD), columnas = rasgos
    for mc, name in CLASSES.items():
        c = cor[(cor.market_class == mc) & (cor.target == "seedyield") & (cor.level == "parcela")]
        if c.empty:
            continue
        piv = c.pivot_table(index=["env", "gdd"], columns="feature", values="r").reindex(columns=REPL_FEATURES)
        fig, ax = style.figure("2col", 0.18 * len(piv) + 1.6)
        im = ax.imshow(piv.to_numpy(), cmap=style.DIV, vmin=-0.8, vmax=0.8, aspect="auto")
        ax.set_xticks(range(len(piv.columns)))
        ax.set_xticklabels([f.replace("_", " ").replace("canopy area m2", "área dosel") for f in piv.columns],
                           rotation=45, ha="right")
        ax.set_yticks(range(len(piv)))
        ax.set_yticklabels([f"{e.replace('_', ' ')} · {g:.0f} GDD" for e, g in piv.index])
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.iat[i, j]
                if np.isfinite(v) and abs(v) >= 0.4:
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.5,
                            color="white" if abs(v) > 0.6 else style.INK)
        fig.colorbar(im, ax=ax, label="r de Pearson con rendimiento", shrink=0.8)
        ax.set_title(f"{name}: correlación rasgo UAV–rendimiento por vuelo (nivel parcela)")
        style.save(fig, OUTDIR / f"fig_correlations_{mc}")
    # Fig. LASSO réplica vs publicado
    cc = comp.dropna(subset=["r2"])
    if not cc.empty:
        fig, ax = style.figure("1.5col", 3.0)
        lab = cc.dataset + " · " + cc.level
        order = sorted(lab.unique())
        y = {k: i for i, k in enumerate(order)}
        z = cc.drop_duplicates(["dataset", "level"])
        ax.scatter(z.r2_zhang, [y[k] for k in z.dataset + " · " + z.level], marker="|", s=120, color=style.INK,
                   label="Zhang et al. (2021)")
        for var, col, off in (("original", style.CAT[0], -0.15), ("anidada", style.CAT[1], 0.15)):
            s = cc[cc.variant == var]
            ax.scatter(s.r2, [y[k] + off for k in s.dataset + " · " + s.level], color=col, s=22,
                       label=f"Réplica ({var})", zorder=3)
        ax.set_yticks(range(len(order))); ax.set_yticklabels([o.replace("_", " ") for o in order])
        ax.set_xlabel("R² de prueba (LASSO, garbanzo kabuli)")
        ax.axvline(0, color=style.GRID, lw=0.8)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        ax.set_title("Réplica del modelo LASSO de rendimiento")
        style.save(fig, OUTDIR / "fig_lasso_vs_zhang")


if __name__ == "__main__":
    main()
