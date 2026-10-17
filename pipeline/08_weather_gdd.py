"""Fase 3a - Clima diario y grados-día (GDD) por campo y por vuelo.

Fuente: Daymet V4 R1, 1 km, diario (Thornton et al. 2022, https://doi.org/10.3334/ORNLDAAC/2129), API de un píxel,
en el centroide real de cada campo (huella del mosaico; en Fairfield el garbanzo está en otro campo).
GDD diario = max(0, (Tmáx + Tmín)/2 − Tbase), Tbase = 3 °C (como Zhang et al. 2021), acumulado desde la siembra
de cada ensayo (hoja Description).
Salidas: outputs/08_weather/{daymet_daily.csv, gdd_by_trial_day.csv, flight_gdd.csv, fig_gdd.png}
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT  # noqa: E402

OUTDIR = OUT / "08_weather"
TBASE = 3.0
API = "https://daymet.ornl.gov/single-pixel/api/data"
YEAR_COL = {2017: "#2a78d6", 2018: "#eb6834", 2019: "#1baf7a"}
INK, MUTED = "#0b0b0b", "#52514e"


def daymet(lat: float, lon: float, year: int) -> pd.DataFrame:
    r = requests.get(API, params=dict(lat=f"{lat:.5f}", lon=f"{lon:.5f}", vars="tmax,tmin,prcp", years=year),
                     timeout=60)
    r.raise_for_status()
    txt = r.text
    d = pd.read_csv(io.StringIO(txt[txt.index("year,yday"):]))
    d.columns = ["year", "yday", "prcp_mm", "tmax_c", "tmin_c"]
    d["date"] = pd.to_datetime(d.year.astype(str), format="%Y") + pd.to_timedelta(d.yday - 1, unit="D")
    return d


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fp = gpd.read_file(OUT / "04_context" / "mosaic_footprints.geojson")
    fields = fp.dissolve(by=["year", "site", "crop"]).reset_index()
    fields["lon"], fields["lat"] = fields.geometry.centroid.x, fields.geometry.centroid.y
    desc = pd.read_csv(OUT / "02_tabular_qc" / "trials_description.csv", dtype={"trial": str},
                       parse_dates=["planting_date"])

    def field_of(row):
        g = fields[(fields.year == row.year) & (fields.site == row.site)]
        crop = row.crop_by_code
        m = g[g.crop == crop]
        return (m if not m.empty else g[g.crop == "pea+chickpea"]).iloc[0] if len(g) else None

    wx, gdd_rows = [], []
    cache = {}
    for _, t in desc.iterrows():
        f = field_of(t)
        if f is None:
            continue
        key = (round(f.lat, 4), round(f.lon, 4), t.year)
        if key not in cache:
            cache[key] = daymet(f.lat, f.lon, t.year).assign(site=t.site, field_crop=f.crop, lat=f.lat, lon=f.lon)
            wx.append(cache[key])
        d = cache[key].copy()
        d = d[d.date >= t.planting_date]
        d["tmean_c"] = (d.tmax_c + d.tmin_c) / 2
        d["gdd"] = (d.tmean_c - TBASE).clip(lower=0)
        d["gdd_cum"] = d.gdd.cumsum()
        d["das"] = (d.date - t.planting_date).dt.days
        gdd_rows.append(d.assign(trial=t.trial, sowing=t.planting_date.date())[
            ["year", "site", "trial", "field_crop", "sowing", "date", "das", "tmax_c", "tmin_c", "prcp_mm", "gdd",
             "gdd_cum"]])
    pd.concat(wx, ignore_index=True).to_csv(OUTDIR / "daymet_daily.csv", index=False)
    gd = pd.concat(gdd_rows, ignore_index=True)
    gd.to_csv(OUTDIR / "gdd_by_trial_day.csv", index=False)

    # GDD en cada vuelo (por ensayo cubierto por el mosaico)
    fl = pd.read_csv(OUT / "01_inventory" / "flight_inventory.csv", parse_dates=["date"])
    rows = []
    for _, f in fl.iterrows():
        g = gd[(gd.year == f.year) & (gd.site == f.site) & (gd.date == f.date)]
        if f.crop in ("pea", "chickpea"):
            g = g[g.trial.str[2].eq("8") == (f.crop == "chickpea")]
        for _, r in g.iterrows():
            rows.append(dict(year=f.year, site=f.site, crop=f.crop, stage=f.stage, flight_dir=f.flight_dir,
                             date=f.date.date(), trial=r.trial, das=r.das, gdd_cum=round(r.gdd_cum, 1)))
    fg = pd.DataFrame(rows)
    fg.to_csv(OUTDIR / "flight_gdd.csv", index=False)

    # Figura: GDD acumulado por sitio-año con los vuelos marcados
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, site in zip(axes, ("Pullman", "Fairfield", "Genesee")):
        for y, col in YEAR_COL.items():
            g = gd[(gd.site == site) & (gd.year == y)]
            if g.empty:
                continue
            first = g[g.trial == g.trial.iloc[0]]
            ax.plot(first.das, first.gdd_cum, color=col, lw=2, label=str(y))
            ff = fg[(fg.site == site) & (fg.year == y)].drop_duplicates("date")
            ax.scatter(ff.das, ff.gdd_cum, color=col, s=22, edgecolor="#fcfcfb", zorder=3)
        ax.set_title(site, loc="left", fontsize=8, color=INK)
        ax.set_xlabel("Días desde la siembra", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.axhspan(721, 772, color="#e6e5e0", zorder=0)
    axes[0].set_ylabel("GDD acumulado (°C·d, base 3 °C)", fontsize=7)
    axes[0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.text(0.01, -0.10, "Puntos = vuelos UAV. Franja gris = floración (721-772 GDD, Zhang et al. 2021). "
             "Clima: Daymet V4 R1 (Thornton et al. 2022).", fontsize=6, color=MUTED)
    fig.savefig(OUTDIR / "fig_gdd.png", dpi=200, bbox_inches="tight")
    print(fg.groupby(["year", "site", "crop"]).agg(n=("date", "nunique"), gdd_min=("gdd_cum", "min"),
                                                   gdd_max=("gdd_cum", "max")).to_string())


if __name__ == "__main__":
    main()
