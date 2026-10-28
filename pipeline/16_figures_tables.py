"""Paso 16 - Figuras y tablas finales de resultados (numeradas, estilo común) y resumen de resultados.

Figuras (outputs/16_figures/figures/):
  Fig1 localización (de `04`) · Fig2 flujo metodológico (nuevo) · Fig3 calibración antes/después (nuevo)
  Fig4 grilla georreferenciada (de `07b`) · Fig5 curvas por clase (`12`) · Fig6 H² por GDD (`13`)
  Fig7 réplica LASSO (`11`) · Fig8 desempeño de modelos (`15`) · Fig9 importancia (`15`)
  Suplementarias: S1 sitios, S2 calendario, S3 GDD, S4 correlaciones, S5 parámetros de curva, S6 fenología, S7 ρ.
Tablas (outputs/16_figures/tables/, CSV + Markdown): T1 ensayos, T2 calibración, T3 réplica vs Zhang,
  T4 heredabilidad, T5 modelos.
Resumen: outputs/16_figures/RESULTS_SUMMARY.md (cifras clave de los resultados).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import style  # noqa: E402
from config import BANDS, OUT  # noqa: E402

OUTDIR = OUT / "16_figures"
FIG, TAB = OUTDIR / "figures", OUTDIR / "tables"


def copy(src: Path, name: str) -> None:
    if src.exists():
        shutil.copy(src, FIG / f"{name}{src.suffix}")
        pdf = src.with_suffix(".pdf")
        if pdf.exists():
            shutil.copy(pdf, FIG / f"{name}.pdf")


def table(df: pd.DataFrame, name: str, caption: str) -> str:
    df.to_csv(TAB / f"{name}.csv", index=False)
    md = f"**{name}.** {caption}\n\n" + df.to_markdown(index=False) + "\n"
    (TAB / f"{name}.md").write_text(md, encoding="utf-8")
    return md


def fig_workflow() -> None:
    fig, ax = style.figure("2col", 2.1)
    ax.set_axis_off(); ax.set_xlim(0, 10); ax.set_ylim(0.2, 3.3)
    steps = [("Datos", "55 ortomosaicos\n5 bandas, DN\n34 Excel + croquis", style.CAT[0]),
             ("Calidad", "Inventario y QC\n(01-03)\nproblemas registrados", style.CAT[0]),
             ("Radiometría", "Línea empírica\ncon Sentinel-2\npor sectores (05)", style.CAT[1]),
             ("Geometría", "Croquis → grilla\nUTM; refinamiento\nafín (06-07b, 09)", style.CAT[1]),
             ("Rasgos", "Índices, cobertura,\ntextura, GDD\n(08, 10)", style.CAT[2]),
             ("Análisis", "Réplica (11)\nCurvas, H², G×E\nfenología (12-14)", style.CAT[3]),
             ("Modelos", "LASSO … XGBoost,\nTempCNN; 4 esquemas\nde validación (15)", style.CAT[6])]
    w, gap = 1.22, 0.2
    for i, (title, body, col) in enumerate(steps):
        x = 0.1 + i * (w + gap)
        ax.add_patch(mpatches.FancyBboxPatch((x, 1.0), w, 2.1, boxstyle="round,pad=0.02,rounding_size=0.08",
                                             fc=col, ec="none", alpha=0.15))
        ax.text(x + w / 2, 2.75, title, ha="center", va="center", fontsize=7.5, fontweight="bold")
        ax.text(x + w / 2, 1.85, body, ha="center", va="center", fontsize=5.6, linespacing=1.3)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + gap - 0.02, 2.05), xytext=(x + w + 0.02, 2.05),
                        arrowprops=dict(arrowstyle="-|>", color=style.MUTED, lw=1))
    ax.text(5, 0.6, "Cada paso = script numerado en pipeline/ · salidas versionadas en outputs/ · "
                     "github.com/jf-floresriera/pea_drone", ha="center", fontsize=6, color=style.MUTED)
    style.save(fig, FIG / "Fig2_workflow")


def fig_calibration() -> None:
    st = pd.read_csv(OUT / "03_spectral" / "spectral_stats.csv")
    pl = pd.read_csv(OUT / "05_radiometric" / "plausibility.csv")
    pl = pl[pl.model == "M3"]
    grp, env = "2018_Pullman_pea", (2018, "Pullman", "pea")
    fig, axes = style.figure("2col", 2.8, ncols=2)
    wl = {b: BANDS[b][0] for b in BANDS}
    dates = sorted(st[st.group == grp].date.unique())
    ramp = style.SEQ(np.linspace(0.35, 1, len(dates)))
    for cls, ls in (("vegetation", "-"), ("soil", "--")):
        for dte, col in zip(dates, ramp):
            s = st[(st.group == grp) & (st.cls == cls) & (st.date == dte)].sort_values("wavelength_nm")
            axes[0].plot(s.wavelength_nm, s.p50, ls, color=col, marker="o", ms=2.5)
            q = pl[(pl.year == env[0]) & (pl.site == env[1]) & (pl.crop == env[2]) & (pl.date == dte) & (pl.cls == cls)]
            if not q.empty:
                axes[1].plot([wl[b] for b in BANDS], [q[b].iloc[0] for b in BANDS], ls, color=col, marker="o", ms=2.5,
                             label=dte if cls == "vegetation" else None)
    axes[0].set_ylabel("DN / 65520 (sin calibrar)"); axes[1].set_ylabel("Reflectancia calibrada (M3)")
    for ax, letter in zip(axes, "ab"):
        ax.set_xlabel("Longitud de onda (nm)"); ax.set_xticks(list(wl.values())); style.panel_label(ax, letter)
    axes[1].legend(title="Fecha (línea continua = dosel,\ndiscontinua = suelo)", loc="upper left", bbox_to_anchor=(1.02, 1))
    style.note(fig, "Medianas por clase (Otsu sobre NDVI) en Pullman 2018, arveja. (a) Mosaico archivado; (b) tras la "
                    "calibración cruzada con Sentinel-2 L2A por sectores (modelo por el origen).")
    style.save(fig, FIG / "Fig3_calibration")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True)
    fig_workflow(); fig_calibration()
    copy(OUT / "04_context" / "fig1_location_map.png", "Fig1_location")
    for p in sorted((OUT / "07_plot_grid" / "check").glob("p07_*.png"))[:1]:
        copy(p, "Fig4_plot_grid")
    copy(OUT / "12_temporal" / "fig_curves_by_class.png", "Fig5_canopy_dynamics")
    copy(OUT / "13_mixed_models" / "fig_h2_by_gdd.png", "Fig6_heritability")
    copy(OUT / "11_replication" / "fig_lasso_vs_zhang.png", "Fig7_replication")
    copy(OUT / "15_models" / "fig_models_r2.png", "Fig8_models")
    copy(OUT / "15_models" / "fig_importance_pea.png", "Fig9_importance_pea")
    copy(OUT / "04_context" / "figS1_trial_sites.png", "FigS1_sites")
    copy(OUT / "04_context" / "figS2_flight_calendar.png", "FigS2_calendar")
    copy(OUT / "08_weather" / "fig_gdd.png", "FigS3_gdd")
    for p in sorted((OUT / "11_replication").glob("fig_correlations_*.png")):
        copy(p, "FigS4_" + p.stem.replace("fig_correlations_", "corr_"))
    copy(OUT / "12_temporal" / "fig_param_distributions.png", "FigS5_curve_params")
    copy(OUT / "14_phenology" / "fig_phenology_obs_pred.png", "FigS6_phenology")
    copy(OUT / "15_models" / "fig_models_spearman.png", "FigS7_models_spearman")
    copy(OUT / "15_models" / "fig_importance_chickpea.png", "FigS8_importance_chickpea")
    copy(OUT / "11_replication" / "fig_sensitivity_normalization.png", "FigS9_sensitivity_normalization")
    copy(OUT / "15_models" / "fig_absolute_features.png", "FigS10_absolute_features")
    copy(OUT / "13_mixed_models" / "fig_rg_yield_by_gdd.png", "FigS11_rg_yield")

    md = ["# Resumen de resultados (generado automáticamente)\n"]
    tc = pd.read_csv(OUT / "02_tabular_qc" / "trial_counts.csv", dtype={"trial": str})
    md.append(table(tc[["year", "site", "trial", "crop_by_code", "n_plots", "n_entries", "yield_mean", "yield_cv",
                        "h2_yield"]].round(2), "Table1_trials", "Ensayos, parcelas, rendimiento medio (kg/ha), CV (%) y "
                                                                 "repetibilidad del rendimiento."))
    co = pd.read_csv(OUT / "05_radiometric" / "calibration_coefficients.csv")
    t2 = co.groupby(["year", "band"]).r2_pooled.first().unstack().round(3).reset_index()
    md.append(table(t2, "Table2_calibration", "R² agrupado de la calibración UAV→Sentinel-2 (modelo adoptado)."))
    p = OUT / "11_replication" / "comparison_zhang2021.csv"
    if p.exists():
        md.append(table(pd.read_csv(p).round(3), "Table3_replication", "R² de prueba de LASSO: publicado vs réplica."))
    p = OUT / "13_mixed_models" / "h2.csv"
    if p.exists():
        h = pd.read_csv(p)
        t4 = (h.assign(kind=np.where(h.flight_dir.isna() | (h.flight_dir == ""), "campo/curva", "UAV por vuelo"))
              .groupby(["market_class", "kind", "trait"]).h2.agg(["median", "min", "max", "count"]).round(2).reset_index())
        md.append(table(t4, "Table4_heritability", "Heredabilidad (H²) por clase comercial y rasgo."))
    p = OUT / "15_models" / "summary.csv"
    if p.exists():
        s = pd.read_csv(p)
        best = s.sort_values("r2_mean", ascending=False).groupby(["crop", "target", "scheme"]).head(1)
        md.append(table(best[["crop", "target", "scheme", "model", "r2_mean", "r2_std", "spearman_mean", "top20_mean"]]
                        .round(3), "Table5_models", "Mejor modelo por cultivo, variable y esquema de validación."))
    for name, path in (("Correlaciones máximas (réplica)", OUT / "11_replication" / "max_correlations.csv"),
                       ("Fenología (CV por genotipo)", OUT / "14_phenology" / "phenology_cv.csv"),
                       ("G×E", OUT / "13_mixed_models" / "gxe.csv"),
                       ("Sensibilidad de la normalización (combinados)",
                        OUT / "11_replication" / "sensitivity_combined_normalization.csv"),
                       ("Rasgos absolutos vs estandarizados (entre ambientes)", OUT / "15_models" / "absolute_features.csv")):
        if path.exists():
            md.append(f"## {name}\n\n" + pd.read_csv(path).round(3).head(40).to_markdown(index=False) + "\n")
    (OUTDIR / "RESULTS_SUMMARY.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Figuras: {len(list(FIG.glob('*.png')))} · Tablas: {len(list(TAB.glob('*.csv')))}")


if __name__ == "__main__":
    main()
