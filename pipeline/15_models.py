"""Paso 7 (Fase 6) - Modelos de Machine Learning / Deep Learning con validación entre genotipos, ambientes y años.

Entradas por parcela (sin fuga de información):
  - rasgos UAV en la grilla común de GDD (400-1150 °C·d; `common.gdd_grid`) + parámetros de curva (`12`);
  - estandarización de rasgos dentro de ambiente (sin usar la variable objetivo).
Variables objetivo: rendimiento (kg/ha), rendimiento estandarizado dentro de ambiente (ranking), días a floración y a
madurez (ambientes con fenología). Cultivos por separado (arveja, garbanzo).
Modelos: LASSO, Elastic Net, PLSR, Random Forest, XGBoost y TempCNN (CNN 1D sobre la serie en GDD; PyTorch).
Esquemas de validación (docs/MODELING_PLAN.md):
  parcela   = KFold(5) aleatorio (comparable con Zhang et al. 2021; optimista)
  genotipo  = GroupKFold(5) por genotipo (todas sus repeticiones y ambientes fuera)
  ambiente  = dejar un sitio-año fuera
  año futuro = entrenar 2017-2018, probar 2019
Métricas: R², RMSE, ρ de Spearman y coincidencia del 20 % superior (por ambiente de prueba).
Importancia: permutación (XGBoost, esquema ambiente) y SHAP (XGBoost, ajuste completo).
Salidas: outputs/15_models/{results.csv, summary.csv, predictions.csv.gz, importance_*.csv, fig_*.png}
"""
from __future__ import annotations

import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNetCV, LassoCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold, KFold, LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from common import CORE_FEATURES, GDD_GRID, gdd_grid, load, plot_table, zscore_within  # noqa: E402
from config import OUT  # noqa: E402

warnings.filterwarnings("ignore")
OUTDIR = OUT / "15_models"
SEED = 0
N_JOBS = max(1, (os.cpu_count() or 4) - 4)
TARGETS = {"yield_z": "Rendimiento (z dentro de ambiente)", "seedyield": "Rendimiento (kg/ha)",
           "fiftyflowr": "Días a floración", "physmatur": "Días a madurez"}
SEQ_FEATURES = ["canopy_cover", "NDVI_mean", "GNDVI_mean", "NDRE_mean", "SAVI_mean", "TVI_mean", "CIrededge_mean",
                "CIgreen_mean", "MCARI_mean", "glcm_contrast"]


# ----------------------------------------------------------------------------------------------- modelos sklearn
def sk_models():
    imp = lambda: SimpleImputer(strategy="median")  # noqa: E731
    return {
        "LASSO": make_pipeline(imp(), StandardScaler(), LassoCV(cv=5, n_alphas=50, max_iter=5000, random_state=SEED)),
        "Elastic Net": make_pipeline(imp(), StandardScaler(),
                                     ElasticNetCV(l1_ratio=[0.2, 0.5, 0.8], cv=5, n_alphas=40, max_iter=5000,
                                                  random_state=SEED)),
        "PLSR": GridSearchCV(make_pipeline(imp(), StandardScaler(), PLSRegression()),
                             {"plsregression__n_components": [2, 4, 6, 8, 12]}, cv=5),
        "Random Forest": make_pipeline(imp(), RandomForestRegressor(n_estimators=500, min_samples_leaf=3,
                                                                    max_features=0.33, n_jobs=N_JOBS,
                                                                    random_state=SEED)),
        "XGBoost": make_pipeline(imp(), XGBRegressor(n_estimators=500, learning_rate=0.03, max_depth=4, subsample=0.8,
                                                     colsample_bytree=0.6, min_child_weight=3, reg_lambda=1.0,
                                                     n_jobs=N_JOBS, random_state=SEED, verbosity=0)),
    }


# ------------------------------------------------------------------------------------------------------- TempCNN
class TempCNNRegressor:
    """CNN 1D sobre la serie (canales = rasgos, tiempo = grilla de GDD), con canal de máscara para valores ausentes."""

    def __init__(self, n_feat: int, n_time: int, epochs: int = 200, seed: int = SEED):
        self.n_feat, self.n_time, self.epochs, self.seed = n_feat, n_time, epochs, seed

    def _tensor(self, X):
        import torch
        A = X.reshape(len(X), self.n_feat, self.n_time)
        mask = np.isfinite(A).astype(np.float32)
        A = np.nan_to_num((A - self.mu) / self.sd)
        return torch.tensor(np.concatenate([A, mask], axis=1), dtype=torch.float32)

    def fit(self, X, y):
        import torch
        from torch import nn
        torch.manual_seed(self.seed); torch.set_num_threads(N_JOBS)
        A = X.reshape(len(X), self.n_feat, self.n_time)
        self.mu = np.nanmean(A, axis=(0, 2), keepdims=True)[0]
        self.sd = np.nanstd(A, axis=(0, 2), keepdims=True)[0] + 1e-6
        self.ym, self.ys = float(np.mean(y)), float(np.std(y) + 1e-6)
        Xt, yt = self._tensor(X), torch.tensor((y - self.ym) / self.ys, dtype=torch.float32)
        c = 2 * self.n_feat
        self.net = nn.Sequential(nn.Conv1d(c, 32, 3, padding=1), nn.BatchNorm1d(32), nn.ReLU(), nn.Dropout(0.2),
                                 nn.Conv1d(32, 32, 3, padding=1), nn.BatchNorm1d(32), nn.ReLU(), nn.Dropout(0.2),
                                 nn.Flatten(), nn.Linear(32 * self.n_time, 32), nn.ReLU(), nn.Dropout(0.2),
                                 nn.Linear(32, 1))
        rng = np.random.default_rng(self.seed)
        idx = rng.permutation(len(Xt)); nv = max(8, int(0.15 * len(Xt)))
        va, tr = idx[:nv], idx[nv:]
        opt = torch.optim.AdamW(self.net.parameters(), lr=1e-3, weight_decay=1e-3)
        best, best_state, wait = np.inf, None, 0
        for _ in range(self.epochs):
            self.net.train()
            for b in np.array_split(rng.permutation(tr), max(1, len(tr) // 64)):
                opt.zero_grad()
                loss = nn.functional.mse_loss(self.net(Xt[b]).squeeze(1), yt[b])
                loss.backward(); opt.step()
            self.net.eval()
            with torch.no_grad():
                vl = nn.functional.mse_loss(self.net(Xt[va]).squeeze(1), yt[va]).item()
            if vl < best - 1e-4:
                best, best_state, wait = vl, {k: v.clone() for k, v in self.net.state_dict().items()}, 0
            else:
                wait += 1
                if wait >= 25:
                    break
        self.net.load_state_dict(best_state)
        return self

    def predict(self, X):
        import torch
        self.net.eval()
        with torch.no_grad():
            return self.net(self._tensor(X)).squeeze(1).numpy() * self.ys + self.ym


# --------------------------------------------------------------------------------------------------------- datos
def build(d: pd.DataFrame):
    pt = plot_table(d)
    feats = [f for f in CORE_FEATURES if f in d]
    G = gdd_grid(d, feats)
    cp = pd.read_csv(OUT / "12_temporal" / "curve_params.csv")
    cpw = cp[cp.trait.isin(["canopy_cover", "NDVI_plotmean", "NDRE_plotmean"])].pivot_table(
        index="plot_uid", columns="trait", values=["x0", "max_rate", "auc", "ymax", "senescence_rate"])
    cpw.columns = [f"{t}:{p}" for p, t in cpw.columns]
    X = G.join(cpw, how="left").reindex(pt.index)
    X = X.loc[:, X.notna().mean() > 0.3]
    env = pt.env
    Xz = X.apply(lambda c: zscore_within(c, env))           # estandarización de rasgos dentro de ambiente
    S = np.stack([gdd_grid_matrix(G.reindex(pt.index), f) for f in SEQ_FEATURES if f"{f}@{GDD_GRID[0]}" in G or
                  any(c.startswith(f + "@") for c in G.columns)], axis=1)
    pt["yield_z"] = zscore_within(pt.seedyield, env)
    return pt, Xz, S


def gdd_grid_matrix(G: pd.DataFrame, f: str) -> np.ndarray:
    cols = [f"{f}@{g}" for g in GDD_GRID]
    return np.column_stack([G[c].to_numpy() if c in G else np.full(len(G), np.nan) for c in cols])


def schemes(pt: pd.DataFrame, idx: np.ndarray):
    sub = pt.iloc[idx]
    yield "parcela", KFold(5, shuffle=True, random_state=SEED).split(idx)
    yield "genotipo", GroupKFold(5).split(idx, groups=sub.entry_name)
    if sub.env.nunique() >= 3:
        yield "ambiente", LeaveOneGroupOut().split(idx, groups=sub.env)
    if sub.year.nunique() >= 2 and (sub.year == 2019).any():
        tr = np.where(sub.year < 2019)[0]; te = np.where(sub.year == 2019)[0]
        if len(tr) > 50 and len(te) > 20:
            yield "año futuro", iter([(tr, te)])


def metrics(y, p, env):
    out = dict(r2=r2_score(y, p), rmse=float(np.sqrt(mean_squared_error(y, p))), spearman=spearmanr(y, p)[0])
    tops = []
    for e in np.unique(env):
        m = env == e
        if m.sum() >= 10:
            k = max(1, int(round(0.2 * m.sum())))
            tops.append(len(set(np.argsort(-y[m])[:k]) & set(np.argsort(-p[m])[:k])) / k)
    out["top20"] = float(np.mean(tops)) if tops else np.nan
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    d = load()
    pt, Xz, S = build(d)
    Xa, Sa = Xz.to_numpy(float), S.reshape(len(S), -1)
    res, preds = [], []
    jobs = [(c, t) for c in ("pea", "chickpea") for t in TARGETS]
    for j, (crop, target) in enumerate(jobs, 1):
        idx = np.where((pt.crop == crop).to_numpy() & pt[target].notna().to_numpy())[0]
        if len(idx) < 60:
            continue
        y_all, env_all = pt[target].to_numpy(float), pt.env.to_numpy()
        for scheme, splits in schemes(pt, idx):
            for fold, (tr, te) in enumerate(splits):
                itr, ite = idx[tr], idx[te]
                for name, model in list(sk_models().items()) + [("TempCNN", None)]:
                    ts = time.time()
                    if name == "TempCNN":
                        m = TempCNNRegressor(S.shape[1], S.shape[2]).fit(Sa[itr], y_all[itr])
                        p = m.predict(Sa[ite])
                    else:
                        m = model.fit(Xa[itr], y_all[itr])
                        p = np.ravel(m.predict(Xa[ite]))
                    r = metrics(y_all[ite], p, env_all[ite])
                    res.append(dict(crop=crop, target=target, scheme=scheme, fold=fold, model=name, n_train=len(itr),
                                    n_test=len(ite), seconds=time.time() - ts, **r))
                    preds.append(pd.DataFrame(dict(plot_uid=pt.index[ite], obs=y_all[ite], pred=p, crop=crop,
                                                   target=target, scheme=scheme, fold=fold, model=name)))
            s = pd.DataFrame(res)
            s = s[(s.crop == crop) & (s.target == target) & (s.scheme == scheme)]
            print(f"[{j}/{len(jobs)}] {crop} {target} {scheme}: " + ", ".join(
                f"{m}={v:.2f}" for m, v in s.groupby("model").r2.mean().items()) + f"  ({(time.time() - t0) / 60:.1f} min)",
                flush=True)
        pd.DataFrame(res).to_csv(OUTDIR / "results.csv", index=False)
    R = pd.DataFrame(res)
    R.to_csv(OUTDIR / "results.csv", index=False)
    pd.concat(preds).to_csv(OUTDIR / "predictions.csv.gz", index=False)
    summ = R.groupby(["crop", "target", "scheme", "model"])[["r2", "rmse", "spearman", "top20"]].agg(["mean", "std"])
    summ.columns = [f"{a}_{b}" for a, b in summ.columns]
    summ.reset_index().to_csv(OUTDIR / "summary.csv", index=False)
    importance(pt, Xz)
    figures(R)
    print(f"total {(time.time() - t0) / 60:.1f} min")


def importance(pt: pd.DataFrame, Xz: pd.DataFrame) -> None:
    import shap
    for crop in ("pea", "chickpea"):
        idx = np.where((pt.crop == crop).to_numpy() & pt.yield_z.notna().to_numpy())[0]
        X, y, env = Xz.iloc[idx], pt.yield_z.iloc[idx].to_numpy(), pt.env.iloc[idx].to_numpy()
        model = sk_models()["XGBoost"]
        imps = []
        for tr, te in LeaveOneGroupOut().split(X, groups=env):
            model.fit(X.iloc[tr], y[tr])
            pi = permutation_importance(model, X.iloc[te], y[te], n_repeats=5, random_state=SEED, n_jobs=N_JOBS)
            imps.append(pd.Series(pi.importances_mean, index=X.columns))
        imp = pd.concat(imps, axis=1).mean(axis=1).sort_values(ascending=False)
        imp.rename("perm_importance").to_csv(OUTDIR / f"importance_perm_{crop}.csv")
        model.fit(X, y)
        Xi = model[0].transform(X)
        sv = shap.TreeExplainer(model[-1]).shap_values(Xi)
        pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False).rename(
            "mean_abs_shap").to_csv(OUTDIR / f"importance_shap_{crop}.csv")
        fig, ax = style.figure("1.5col", 3.4)
        top = imp.head(15)[::-1]
        ax.barh([style.wrap(i.replace("_", " "), 30) for i in top.index], top.values, color=style.CROP[crop])
        ax.set_xlabel("Importancia por permutación (Δ R², dejar-un-ambiente-fuera)")
        ax.set_title(f"XGBoost, rendimiento (z) - {'arveja' if crop == 'pea' else 'garbanzo'}")
        style.save(fig, OUTDIR / f"fig_importance_{crop}")


def figures(R: pd.DataFrame) -> None:
    order = ["parcela", "genotipo", "ambiente", "año futuro"]
    models = ["LASSO", "Elastic Net", "PLSR", "Random Forest", "XGBoost", "TempCNN"]
    for metric, lab in (("r2", "R²"), ("spearman", "ρ de Spearman")):
        fig, axes = style.figure("2col", 4.2, nrows=2, ncols=2, sharex=True)
        for ax, (crop, target), letter in zip(axes.flat, [("pea", "yield_z"), ("pea", "seedyield"),
                                                          ("chickpea", "yield_z"), ("chickpea", "seedyield")], "abcd"):
            s = R[(R.crop == crop) & (R.target == target)]
            for i, m in enumerate(models):
                q = s[s.model == m].groupby("scheme")[metric].agg(["mean", "std"]).reindex(order)
                x = np.arange(len(order)) + (i - 2.5) * 0.12
                ax.errorbar(x, q["mean"], yerr=q["std"], fmt="o", ms=3.5, color=style.CAT[i], capsize=1.5, lw=0.8,
                            label=m)
            ax.axhline(0, color=style.GRID, lw=0.8)
            ax.set_xticks(range(len(order))); ax.set_xticklabels(order)
            ax.set_ylabel(lab)
            ax.set_title(f"({letter}) {'Arveja' if crop == 'pea' else 'Garbanzo'} · {style.wrap(TARGETS[target], 30)}",
                         loc="left")
        axes[0, 1].legend(loc="upper left", bbox_to_anchor=(1.02, 1))
        style.note(fig, "Media ± DE entre particiones. Esquemas: parcela = KFold aleatorio; genotipo = GroupKFold por "
                        "genotipo; ambiente = dejar un sitio-año fuera; año futuro = 2017-2018 → 2019.")
        style.save(fig, OUTDIR / f"fig_models_{metric}")


if __name__ == "__main__":
    main()
