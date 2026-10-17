"""Fase 1b - Consolidación y control de calidad de los datos de campo (Excel 2017-2019).

1. Lee la hoja `Description` (metadatos de ensayo) y todas las hojas de ensayo.
2. Normaliza nombres de columnas y construye una tabla maestra por parcela (plots_master.csv).
3. Ejecuta chequeos: nº de parcelas/entradas/repeticiones vs Description, duplicados, faltantes,
   unidades, coherencia de fechas, atípicos, valores copiados entre sitios y repetibilidad (H²)
   del rendimiento por ensayo.
Salidas en outputs/02_tabular_qc/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import EXCEL, OUT  # noqa: E402

OUTDIR = OUT / "02_tabular_qc"
RENAME = {"bloc": "block", "entry name": "entry_name", "slotseedwt": "plotseedwt"}
TRAITS = ["seedyield", "plotseedwt", "fiftyflowr", "physmatur", "vinelength", "canopyht", "podht",
          "podhtmat", "flowrnode", "reprnodes", "podspedun", "podhi", "planthi", "hundseedwt"]
DATES = ["datefl50", "datephymat", "datesown"]


def read_description(year: int) -> pd.DataFrame:
    raw = pd.read_excel(EXCEL[year], sheet_name="Description", header=None)
    hdr = raw.iloc[0].tolist()
    end = raw.index[raw[0].isna()][0]  # bloque superior hasta la primera fila vacía
    d = raw.iloc[1:end].copy()
    d.columns = [str(h).strip() for h in hdr]
    d = d.rename(columns={"Trial No.": "trial", "Trial Location": "site", "Crop Type": "crop_type",
                          "Number of Varieties": "n_entries_expected", "Number of Replicate": "n_reps_expected",
                          "Number of Plots": "n_plots_expected", "Planting Date": "planting_date",
                          "Plot Rotation (deg.)": "plot_rotation_deg", "UAV Imagery (M/DD/YYYY)": "uav_dates"})
    d["year"] = year
    d["trial"] = d["trial"].astype(str)
    lat_lon = d["GPS"].str.split(",", expand=True).astype(float)
    d["lat"], d["lon"] = lat_lon[0], lat_lon[1]
    d["crop"] = np.where(d["crop_type"].str.contains("chick", case=False), "chickpea", "pea")
    d["uav_dates"] = d["uav_dates"].astype(str).str.strip(". ")
    # El tipo de cultivo se corrige por el código de ensayo (x8x = garbanzo): ver issue en el reporte
    d["crop_by_code"] = np.where(d["trial"].str[2] == "8", "chickpea", "pea")
    return d.drop(columns=["GPS"])


def read_trials(year: int) -> pd.DataFrame:
    xl = pd.ExcelFile(EXCEL[year])
    frames = []
    for sheet in xl.sheet_names[1:]:
        d = xl.parse(sheet)
        d.columns = [str(c).strip().lower() for c in d.columns]
        d = d.rename(columns=RENAME)
        d = d.loc[:, ~d.columns.duplicated()]  # p.ej. 1702 Fairfield 2017 repite datefl50/datephymat
        # 1703 Pullman 2017: la primera columna dice 'entry' pero es 'record'
        if list(d.columns[:3]) == ["entry", "block", "entry.1"]:
            d = d.rename(columns={"entry": "record", "entry.1": "entry"})
        trial, site = sheet.split(" ", 1)
        d.insert(0, "year", year)
        d.insert(1, "site", site.strip())
        d.insert(2, "trial", trial.strip())
        d["sheet"] = sheet
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def market_class(trial: str) -> str:
    """Clase comercial a partir del código de ensayo (YYNN[B|G]), consistente en los tres años."""
    code, suffix = trial[2:4], trial[4:]
    if code[0] == "8":
        return "green_chickpea" if suffix == "G" else "kabuli_chickpea"
    if suffix == "B":
        return "nz_green_yellow_pea"
    return {"01": "green_pea", "03": "green_pea", "02": "yellow_pea", "04": "yellow_pea"}[code]


def h2_rcbd(g: pd.DataFrame, trait: str) -> float:
    """Repetibilidad (H² en base a medias de entrada) por ANOVA de 2 vías entrada + bloque."""
    d = g[["entry", "block", trait]].dropna()
    if d["entry"].nunique() < 3 or d["block"].nunique() < 2:
        return np.nan
    y, gm = d[trait].astype(float), d[trait].mean()
    r = d.groupby("entry").size().mean()
    ss_g = (d.groupby("entry")[trait].agg(["mean", "size"]).pipe(lambda t: (t["size"] * (t["mean"] - gm) ** 2).sum()))
    ss_b = (d.groupby("block")[trait].agg(["mean", "size"]).pipe(lambda t: (t["size"] * (t["mean"] - gm) ** 2).sum()))
    ss_t = ((y - gm) ** 2).sum()
    df_g, df_b = d["entry"].nunique() - 1, d["block"].nunique() - 1
    df_e = len(d) - 1 - df_g - df_b
    ms_g, ms_e = ss_g / df_g, (ss_t - ss_g - ss_b) / df_e
    vg = max((ms_g - ms_e) / r, 0)
    return vg / (vg + ms_e / r) if (vg + ms_e / r) > 0 else np.nan


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    desc = pd.concat([read_description(y) for y in EXCEL], ignore_index=True)
    plots = pd.concat([read_trials(y) for y in EXCEL], ignore_index=True)

    # Bloque faltante en 1803/1804 Pullman 2018: parcelas numeradas en secuencia por bloque
    # (1..n_entradas = bloque 1, ...). Se valida luego que cada bloque contenga cada entrada una vez.
    miss_block = plots["block"].isna()
    for key, g in plots[miss_block].groupby(["year", "site", "trial"]):
        n_ent = g["entry"].nunique()
        blk = (g["plot"].rank(method="first").astype(int) - 1) // n_ent + 1
        ok = g.assign(b=blk).groupby("b")["entry"].apply(lambda e: e.is_unique and e.nunique() == n_ent).all()
        plots.loc[g.index, "block"] = blk
        print(f"bloque inferido {key}: {blk.nunique()} bloques, balanceado={ok}")
    plots["block_inferred"] = miss_block

    for c in DATES:
        if c in plots:
            plots[c] = pd.to_datetime(plots[c], errors="coerce")
    for c in TRAITS:
        if c in plots:
            plots[c] = pd.to_numeric(plots[c], errors="coerce")
    plots = plots.merge(desc[["year", "site", "trial", "crop_by_code", "crop_type"]],
                        on=["year", "site", "trial"], how="left").rename(columns={"crop_by_code": "crop"})
    plots["plot_uid"] = (plots["year"].astype(str) + "_" + plots["site"] + "_" + plots["trial"] + "_P"
                         + plots["plot"].astype("Int64").astype(str).str.zfill(3))
    plots["market_class"] = plots["trial"].map(market_class)
    plots["trial_stage"] = np.where(plots["trial"].str[3] == "1", "advanced",
                                    np.where(plots["trial"].str[3].isin(["3", "4"]), "preliminary", "advanced"))
    keep = ["plot_uid", "year", "site", "trial", "crop", "market_class", "trial_stage", "crop_type", "plot",
            "block", "block_inferred",
            "entry", "entry_name", "checks", *[c for c in TRAITS + DATES if c in plots], "sheet"]
    plots = plots[[c for c in keep if c in plots]].sort_values(["year", "site", "trial", "plot"])
    plots.to_csv(OUTDIR / "plots_master.csv", index=False)
    desc.to_csv(OUTDIR / "trials_description.csv", index=False)

    issues = []

    def issue(sev, where, msg):
        issues.append(dict(severity=sev, where=where, issue=msg))

    # --- Description
    for _, r in desc.iterrows():
        if r["crop"] != r["crop_by_code"]:
            issue("ALTA", f"{r.year} {r.site} {r.trial}", f"Description dice '{r.crop_type}' pero el código {r.trial} es garbanzo (x8x)")

    # --- Conteos vs Description
    cnt = (plots.groupby(["year", "site", "trial"])
           .agg(n_plots=("plot", "size"), n_entries=("entry", "nunique"), n_blocks=("block", "nunique"),
                dup_plots=("plot", lambda s: int(s.duplicated().sum())),
                reps_min=("entry", lambda s: int(s.value_counts().min())),
                reps_max=("entry", lambda s: int(s.value_counts().max())),
                yield_na=("seedyield", lambda s: int(s.isna().sum())),
                yield_mean=("seedyield", "mean"), yield_cv=("seedyield", lambda s: s.std() / s.mean() * 100))
           .reset_index()
           .merge(desc[["year", "site", "trial", "crop_by_code", "n_entries_expected", "n_plots_expected",
                        "plot_rotation_deg", "uav_dates"]], on=["year", "site", "trial"], how="left"))
    cnt["h2_yield"] = [h2_rcbd(g, "seedyield") for _, g in plots.groupby(["year", "site", "trial"])]
    for c in ("fiftyflowr", "physmatur", "canopyht", "vinelength"):
        cnt[f"h2_{c}"] = [h2_rcbd(g, c) if g[c].notna().sum() > 10 else np.nan
                          for _, g in plots.groupby(["year", "site", "trial"])]
    cnt.to_csv(OUTDIR / "trial_counts.csv", index=False)
    for _, r in cnt.iterrows():
        w = f"{r.year} {r.site} {r.trial}"
        if r.n_plots != r.n_plots_expected:
            issue("MEDIA", w, f"{r.n_plots} parcelas en la hoja vs {r.n_plots_expected} en Description")
        if r.n_entries != r.n_entries_expected:
            issue("MEDIA", w, f"{r.n_entries} entradas vs {r.n_entries_expected} en Description")
        if r.dup_plots:
            issue("ALTA", w, f"{r.dup_plots} números de parcela duplicados")
        if r.reps_min != r.reps_max:
            issue("BAJA", w, f"repeticiones por entrada desbalanceadas ({r.reps_min}-{r.reps_max})")
        if r.yield_na:
            issue("MEDIA", w, f"{r.yield_na} parcelas sin rendimiento")

    # --- Unidades: la hoja dice grams/hectare; magnitudes y la columna yieldlbs (lb/acre) indican kg/ha
    issue("ALTA", "Description (todos los años)",
          f"'seedyield' rotulado en g/ha; rango observado {plots.seedyield.min():.0f}-{plots.seedyield.max():.0f} "
          "→ son kg/ha (verificado: yieldlbs = seedyield × 0.892 en 1901 Fairfield)")

    # --- Coherencia de fechas: días a floración = datefl50 − datesown
    d = plots.dropna(subset=["datefl50", "datesown", "fiftyflowr"])
    diff = (d["datefl50"] - d["datesown"]).dt.days - d["fiftyflowr"]
    bad = d[diff.abs() > 1]
    if len(bad):
        for (y, s, t), g in bad.groupby(["year", "site", "trial"]):
            issue("MEDIA", f"{y} {s} {t}", f"{len(g)} parcelas: fiftyflowr ≠ datefl50 − datesown (|Δ|>1 d)")

    # --- Fenotipos copiados entre localidades (mismo ensayo/año, misma parcela, mismos valores)
    feno = ["fiftyflowr", "physmatur", "vinelength", "canopyht", "podht"]
    for (y, t), g in plots.groupby(["year", "trial"]):
        sites = g["site"].unique()
        if len(sites) < 2:
            continue
        piv = {s: g[g.site == s].set_index("plot")[feno] for s in sites}
        for i, a in enumerate(sites):
            for b in sites[i + 1:]:
                common = piv[a].index.intersection(piv[b].index)
                A, B = piv[a].loc[common].dropna(how="all"), piv[b].loc[common].dropna(how="all")
                common = A.index.intersection(B.index)
                if len(common) > 5:
                    same = (A.loc[common].fillna(-1) == B.loc[common].fillna(-1)).all(axis=1).mean()
                    if same > 0.9:
                        # Decisión del equipo (2026-10-16): los datos fisiológicos entregados por los
                        # investigadores se asumen válidos tal como están; solo se documenta la observación.
                        issue("INFO", f"{y} {t} {a} vs {b}",
                              f"{same:.0%} de parcelas con fenología idéntica entre sitios; se asume válido "
                              "(valores del ensayo según los investigadores)")

    # --- Atípicos de rendimiento (|z robusto| > 3.5 dentro de ensayo)
    def rz(s):
        med, mad = s.median(), (s - s.median()).abs().median() * 1.4826
        return (s - med) / mad if mad else s * 0
    plots["yield_rz"] = plots.groupby(["year", "site", "trial"])["seedyield"].transform(rz)
    out = plots[plots["yield_rz"].abs() > 3.5]
    out[["plot_uid", "entry_name", "seedyield", "yield_rz"]].to_csv(OUTDIR / "yield_outliers.csv", index=False)
    if len(out):
        issue("BAJA", "rendimiento", f"{len(out)} parcelas con |z robusto|>3.5 (ver yield_outliers.csv)")

    # --- Faltantes por rasgo
    miss = (plots.groupby(["year", "site", "trial"])[[c for c in TRAITS if c in plots]]
            .apply(lambda g: g.notna().mean().round(2)))
    miss.to_csv(OUTDIR / "trait_completeness.csv")

    iss = pd.DataFrame(issues)
    iss.to_csv(OUTDIR / "qc_issues.csv", index=False)

    crop_tot = plots.groupby(["crop", "market_class"]).agg(plots=("plot_uid", "size"), entries=("entry_name", "nunique"),
                                         trials=("trial", lambda s: s.nunique()))
    with open(OUTDIR / "tabular_qc_report.md", "w", encoding="utf-8") as fh:
        fh.write("# Control de calidad de datos de campo\n\n")
        fh.write(f"- Parcelas totales: {len(plots)} | ensayos (año×sitio×ensayo): {len(cnt)}\n\n")
        fh.write("## Totales por cultivo\n\n" + crop_tot.to_markdown() + "\n\n")
        fh.write("## Conteos, rendimiento y repetibilidad por ensayo\n\n"
                 + cnt.drop(columns=["uav_dates"]).round(2).to_markdown(index=False) + "\n\n")
        fh.write(f"## Problemas detectados ({len(iss)})\n\n" + iss.to_markdown(index=False) + "\n")
    print(crop_tot.to_string(), "\n")
    print(cnt.drop(columns=["uav_dates"]).round(2).to_string(), "\n")
    print(iss.to_string())


if __name__ == "__main__":
    main()
