"""Fase 1d - Mapas de contexto: dónde y cuándo se realizaron los ensayos (Figura 1 y figuras de contexto S1-S2).

Fig. 1  Localización: (a) EE. UU. con WA/ID, (b) región del Palouse con los ensayos por año.
Fig. S1 Ensayos por sitio × año: ortomosaico CIR (submuestreado, georreferenciado) sobre imagen satelital.
Fig. S2 Calendario de vuelos UAV por sitio-año con fecha de siembra y completitud de bandas.
Salidas: outputs/04_context/{fig1_location_map.png, figS1_trial_sites.png, figS2_flight_calendar.png,
         mosaic_footprints.geojson}

Datos externos (descarga abierta, no versionados, en data_ext/):
  Natural Earth 10m admin-1 (naciscdn.org) y US Census cartographic boundary counties 2023 (5m).
"""
from __future__ import annotations

import sys
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from rasterio import features  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.warp import Resampling as WarpResampling, calculate_default_transform, reproject  # noqa: E402
from shapely.geometry import shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT, ROOT  # noqa: E402

OUTDIR = OUT / "04_context"
EXT = ROOT / "data_ext"
WEB = "EPSG:3857"
CROP_MARK = {"pea": "o", "chickpea": "D", "pea+chickpea": "s"}
CROP_ES = {"pea": "arveja", "chickpea": "garbanzo", "pea+chickpea": "arveja + garbanzo"}
YEAR_COL = {2017: "#2a78d6", 2018: "#eb6834", 2019: "#1baf7a"}  # slots categóricos 1-3 (validados all-pairs)
SITE_MARK = {"Pullman": "o", "Fairfield": "s", "Genesee": "^"}
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
DECIM = 16
SITES = ["Pullman", "Fairfield", "Genesee"]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "figure.dpi": 150, "savefig.bbox": "tight", "savefig.dpi": 300})


def scalebar(ax, length_m: float, lat: float, label: str, loc=(0.05, 0.06), color=INK):
    """Barra de escala en EPSG:3857 corrigiendo la deformación de Mercator a la latitud dada."""
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    L = length_m / np.cos(np.radians(lat))
    x, y = x0 + loc[0] * (x1 - x0), y0 + loc[1] * (y1 - y0)
    ax.plot([x, x + L], [y, y], color=color, lw=3, solid_capstyle="butt")
    ax.text(x + L / 2, y + 0.02 * (y1 - y0), label, ha="center", va="bottom", color=color, fontsize=7)


def north_arrow(ax, loc=(0.93, 0.88), color=INK):
    ax.annotate("N", xy=loc, xytext=(loc[0], loc[1] - 0.1), xycoords="axes fraction", ha="center", va="center",
                color=color, fontsize=8, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2))


def load_trials() -> pd.DataFrame:
    frames = []
    for y in (2017, 2018, 2019):
        raw = pd.read_excel(ROOT / f"{y}PulseDataset.xlsx", sheet_name="Description", header=None)
        end = raw.index[raw[0].isna()][0]
        d = raw.iloc[1:end, :11].copy()
        d.columns = ["trial", "site", "gps", "crop_type", "n_var", "n_rep", "n_plots", "sowing", "season",
                     "rotation", "uav_dates"]
        d["year"] = y
        frames.append(d)
    t = pd.concat(frames, ignore_index=True)
    t[["lat", "lon"]] = t["gps"].str.split(",", expand=True).astype(float)
    t["trial"] = t["trial"].astype(str)
    t["crop"] = np.where(t["trial"].str[2] == "8", "chickpea", "pea")
    t["sowing"] = pd.to_datetime(t["sowing"])
    return t


def representative_flights() -> pd.DataFrame:
    """Un vuelo por sitio-año-cultivo con NIR/R/G disponibles, el más cercano al 5 de julio."""
    inv = pd.read_csv(OUT / "01_inventory" / "image_inventory.csv")
    inv = inv[inv.status == "OK"]
    cir = inv.groupby("flight_dir").filter(lambda g: {"nir", "red", "green"} <= set(g.band))
    cir = cir[cir.band.isin(["nir", "red", "green"])].copy()
    cir["date"] = pd.to_datetime(cir["date"])
    cir["dist"] = (cir["date"] - pd.to_datetime(cir["year"].astype(str) + "-07-05")).abs()
    best = (cir.sort_values("dist").groupby(["year", "site", "crop", "stage"], dropna=False)["flight_dir"]
            .first().reset_index())
    return cir[cir.flight_dir.isin(best.flight_dir)]


def read_cir_3857(paths: dict[str, Path]):
    """Lee NIR/R/G submuestreados, devuelve RGB (CIR) reproyectado a 3857, su extensión y el contorno válido."""
    bands, alpha = [], None
    with rasterio.open(paths["nir"]) as r0:
        h, w = r0.height // DECIM, r0.width // DECIM
        tr = r0.transform * r0.transform.scale(r0.width / w, r0.height / h)
        crs = r0.crs
    for b in ("nir", "red", "green"):
        with rasterio.open(paths[b]) as r:
            d = r.read(out_shape=(r.count, h, w), resampling=Resampling.average).astype(np.float32)
        bands.append(d[0])
        a = d[-1] > 0 if d.shape[0] > 1 else d[0] > 0
        alpha = a if alpha is None else alpha & a
    footprint = unary_union([shape(g) for g, v in features.shapes(alpha.astype(np.uint8), mask=alpha, transform=tr)
                             if v == 1]).buffer(0)
    dst_tr, dw, dh = calculate_default_transform(crs, WEB, w, h, *rasterio.transform.array_bounds(h, w, tr))
    rgba = np.zeros((dh, dw, 4), np.float32)
    for i, arr in enumerate(bands):
        lo, hi = np.percentile(arr[alpha], [2, 98])
        src = np.where(alpha, np.clip((arr - lo) / (hi - lo + 1e-9), 0, 1), np.nan).astype(np.float32)
        dst = np.full((dh, dw), np.nan, np.float32)
        reproject(src, dst, src_transform=tr, src_crs=crs, dst_transform=dst_tr, dst_crs=WEB,
                  resampling=WarpResampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
        rgba[..., i] = np.nan_to_num(dst)
        if i == 0:
            rgba[..., 3] = np.isfinite(dst).astype(np.float32)
    left, top = dst_tr.c, dst_tr.f
    extent = (left, left + dw * dst_tr.a, top + dh * dst_tr.e, top)
    return rgba, extent, footprint, crs


def fig_location(trials: pd.DataFrame, fp: gpd.GeoDataFrame) -> None:
    states = gpd.read_file(EXT / "ne" / "states.zip")
    us = states[(states.adm0_a3 == "USA") & ~states.name.isin(["Alaska", "Hawaii"])].to_crs("EPSG:5070")
    counties = gpd.read_file(EXT / "census" / "counties.zip")
    cnty = counties[((counties.STATEFP == "53") & counties.NAME.isin(["Whitman", "Spokane"]))
                    | ((counties.STATEFP == "16") & (counties.NAME == "Latah"))].to_crs(WEB)
    st_web = states[states.name.isin(["Washington", "Idaho"])].to_crs(WEB)
    # Ubicación real de cada campo = centroide del ortomosaico (Description trae un solo GPS por sitio, y en
    # Fairfield el garbanzo está en otro campo a 2-6 km de la arveja)
    cen = fp.to_crs(WEB).copy()
    cen["geometry"] = cen.geometry.centroid

    W, H = 7.2, 4.4
    fig = plt.figure(figsize=(W, H))
    ax_a = fig.add_axes([0.0, 0.50, 0.36, 0.47])
    ax_t = fig.add_axes([0.02, 0.06, 0.32, 0.36]); ax_t.set_axis_off()
    ax_b = fig.add_axes([0.40, 0.06, 0.59, 0.91])

    # (a) EE. UU.
    us.plot(ax=ax_a, color="#e6e5e0", edgecolor="white", lw=0.4)
    us[us.name.isin(["Washington", "Idaho"])].plot(ax=ax_a, color="#b9b7ae", edgecolor="white", lw=0.4)
    study = gpd.GeoSeries([fp.union_all().envelope.buffer(0.25)], crs=4326).to_crs("EPSG:5070")
    study.boundary.plot(ax=ax_a, color=INK, lw=1.2)
    for n, xy in (("WA", (-120.5, 47.4)), ("ID", (-114.6, 44.3)), ("OR", (-120.6, 43.9))):
        p = gpd.GeoSeries(gpd.points_from_xy([xy[0]], [xy[1]]), crs=4326).to_crs("EPSG:5070").iloc[0]
        ax_a.text(p.x, p.y, n, fontsize=6.5, color=INK, ha="center", va="center")
    ax_a.set_axis_off(); ax_a.set_title("(a)", loc="left", color=INK)

    # (b) Palouse: extensión con la proporción del panel alrededor de todos los campos
    b = cen.total_bounds
    cxm, cym = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    hh = (b[3] - b[1]) / 2 + 9000
    hw = hh * (0.59 * W) / (0.91 * H)
    ax_b.set_xlim(cxm - hw, cxm + hw); ax_b.set_ylim(cym - hh, cym + hh)
    cx.add_basemap(ax_b, crs=WEB, source=cx.providers.Esri.WorldShadedRelief, attribution=False, zoom=10)
    st_web.boundary.plot(ax=ax_b, color=INK, lw=1.0, linestyle="--")
    cnty.boundary.plot(ax=ax_b, color=MUTED, lw=0.6)
    x0, x1 = ax_b.get_xlim(); y0, y1 = ax_b.get_ylim()
    view = gpd.GeoSeries.from_wkt([f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"], crs=WEB).iloc[0]
    for _, c in cnty.iterrows():
        vis = c.geometry.intersection(view)
        if not vis.is_empty:
            rp = vis.representative_point()
            ax_b.text(rp.x, rp.y, f"{c.NAME} Co.", fontsize=6.5, color=MUTED, style="italic", ha="center")
    off = {2017: -1500, 2018: 0, 2019: 1500}  # desplaza años en el mismo campo para que no se tapen
    for _, r in cen.iterrows():
        ax_b.scatter(r.geometry.x + off[r.year], r.geometry.y, s=40, marker=CROP_MARK[r.crop],
                     color=YEAR_COL[r.year], edgecolor=SURFACE, linewidth=1.2, zorder=5)
    for s, g in cen.groupby("site"):
        ax_b.annotate(s, (g.geometry.x.mean(), g.geometry.y.max()), xytext=(8, 8), textcoords="offset points",
                      fontsize=8.5, fontweight="bold", color=INK,
                      bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none", alpha=0.85))
    ax_b.text(0.02, 0.5, "WASHINGTON", transform=ax_b.transAxes, rotation=90, fontsize=7, color=MUTED, va="center")
    ax_b.text(0.98, 0.5, "IDAHO", transform=ax_b.transAxes, rotation=90, fontsize=7, color=MUTED, va="center",
              ha="right")
    scalebar(ax_b, 10000, fp.union_all().centroid.y, "10 km", loc=(0.08, 0.04))
    north_arrow(ax_b)
    ax_b.set_xticks([]); ax_b.set_yticks([])
    ax_b.set_title("(b)", loc="left", color=INK)
    handles = [Line2D([], [], marker="o", ls="", color=YEAR_COL[y], mec=SURFACE, ms=7, label=str(y)) for y in YEAR_COL]
    handles += [Line2D([], [], marker=CROP_MARK[c], ls="", color=MUTED, mec=SURFACE, ms=6, label=CROP_ES[c])
                for c in CROP_MARK]
    ax_b.legend(handles=handles, loc="center left", bbox_to_anchor=(0.06, 0.32), frameon=True, facecolor=SURFACE, edgecolor="none",
                framealpha=0.9, fontsize=6.5, ncol=2)
    fig.text(0.99, 0.01, "Relieve: Esri World Shaded Relief · Límites: US Census 2023, Natural Earth",
             fontsize=5, color=MUTED, ha="right")

    # tabla resumen debajo de (a)
    summ = (trials.groupby(["site", "year"]).agg(trials=("trial", "nunique"), plots=("n_plots", "sum"))
            .reset_index())
    piv = summ.pivot(index="site", columns="year", values="plots").reindex(SITES).fillna(0).astype(int)
    tb = ax_t.table(cellText=piv.values, rowLabels=piv.index, colLabels=[str(c) for c in piv.columns],
                    loc="center", cellLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(7); tb.scale(1, 1.4)
    for (r_, c_), cell in tb.get_celld().items():
        cell.set_edgecolor("#d9d8d3")
        if r_ == 0 and c_ >= 0:
            cell.set_text_props(color=YEAR_COL[int(piv.columns[c_])], fontweight="bold")
    ax_t.set_title("Parcelas por sitio y año", fontsize=7, color=INK, loc="left")
    fig.savefig(OUTDIR / "fig1_location_map.png"); plt.close(fig)


def fig_sites(trials: pd.DataFrame) -> gpd.GeoDataFrame:
    """Un panel por campo: mosaicos del mismo sitio-año con centros a < 300 m comparten panel."""
    fl = representative_flights()
    items = []
    for (site, year, fdir), g in fl.groupby(["site", "year", "flight_dir"]):
        rgba, ext, footprint, crs = read_cir_3857({r.band: ROOT / r.path for r in g.itertuples()})
        r0 = g.iloc[0]
        items.append(dict(site=site, year=year, crop=r0.crop, date=r0.date, flight_dir=fdir, rgba=rgba, ext=ext,
                          geometry=footprint, crs=crs.to_string(),
                          center=((ext[0] + ext[1]) / 2, (ext[2] + ext[3]) / 2)))
    panels = []
    for site in SITES:
        for year in (2017, 2018, 2019):
            for it in sorted((i for i in items if i["site"] == site and i["year"] == year),
                             key=lambda i: i["crop"], reverse=True):
                same = [p for p in panels if p["site"] == site and p["year"] == year
                        and np.hypot(*np.subtract(p["items"][0]["center"], it["center"])) < 300]
                if same:
                    same[0]["items"].append(it)
                else:
                    panels.append(dict(site=site, year=year, items=[it]))

    ncol = 4
    nrow = int(np.ceil(len(panels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(7.2, 1.95 * nrow + 0.3), squeeze=False)
    for ax in axes.flat[len(panels):]:
        ax.set_axis_off()
    for ax, p in zip(axes.flat, panels):
        e = np.array([i["ext"] for i in p["items"]])
        x0, x1, y0, y1 = e[:, 0].min(), e[:, 1].max(), e[:, 2].min(), e[:, 3].max()
        cxm, cym, half = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 + 40
        ax.set_xlim(cxm - half, cxm + half); ax.set_ylim(cym - half, cym + half)
        cx.add_basemap(ax, crs=WEB, source=cx.providers.Esri.WorldImagery, attribution=False, zoom=18)
        for it in p["items"]:
            ax.imshow(it["rgba"], extent=it["ext"], zorder=3, interpolation="nearest")
        crops = sorted({i["crop"] for i in p["items"]})
        has = {c for c in ("pea", "chickpea") if any(c in k.split("+") for k in crops)}
        tt = trials[(trials.site == p["site"]) & (trials.year == p["year"]) & trials.crop.isin(has)]
        dates = ", ".join(sorted({i["date"].strftime("%d-%b") for i in p["items"]}))
        ax.set_title(f"{p['site']} {p['year']}", loc="left", color=INK, fontsize=7.5, fontweight="bold", pad=2)
        tr = sorted(tt.trial.unique())
        tr_txt = "\n".join(", ".join(tr[k:k + 4]) for k in range(0, len(tr), 4))
        ax.text(0.02, 0.02, f"{' + '.join(CROP_ES[c] for c in crops)}\n{tr_txt}\n"
                f"CIR {dates}", transform=ax.transAxes, fontsize=5.2, color=INK, va="bottom",
                bbox=dict(fc=SURFACE, ec="none", alpha=0.85, pad=1.2))
        lat = gpd.GeoSeries([p["items"][0]["geometry"]], crs=p["items"][0]["crs"]).to_crs(4326).iloc[0].centroid.y
        scalebar(ax, 25, lat, "25 m", loc=(0.70, 0.86), color="white")
        ax.set_xticks([]); ax.set_yticks([])
    fig.text(0.01, 0.003, "Ortomosaicos UAV en falso color (NIR-R-G), fecha más cercana al 5 de julio, sobre Esri World "
             "Imagery (Esri, Maxar, Earthstar Geographics). Genesee 2017: ensayo perdido.", fontsize=5.5, color=MUTED)
    fig.tight_layout(h_pad=0.5, w_pad=0.3, rect=(0, 0.015, 1, 1))
    fig.savefig(OUTDIR / "figS1_trial_sites.png"); plt.close(fig)

    keep = ("year", "site", "crop", "flight_dir", "geometry")
    out = [gpd.GeoDataFrame([{**{k: i[k] for k in keep}, "date": i["date"].date().isoformat()}
                             for i in items if i["crs"] == crs], geometry="geometry", crs=crs).to_crs(4326)
           for crs in sorted({i["crs"] for i in items})]
    return gpd.GeoDataFrame(pd.concat(out, ignore_index=True), crs=4326)


def fig_calendar(trials: pd.DataFrame) -> None:
    fl = pd.read_csv(OUT / "01_inventory" / "flight_inventory.csv", parse_dates=["date"])
    fl["doy"] = fl.date.dt.dayofyear
    sow = trials.groupby(["year", "site"]).sowing.min().dt.dayofyear
    rows = [(y, s) for y in (2017, 2018, 2019) for s in SITES]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for k, (y, s) in enumerate(rows):
        yk = len(rows) - 1 - k
        ax.axhspan(yk - 0.45, yk + 0.45, color="#f2f1ed" if k % 2 == 0 else SURFACE, zorder=0, lw=0)
        if (y, s) in sow.index:
            ax.plot([sow[(y, s)]] * 2, [yk - 0.35, yk + 0.35], color=MUTED, lw=1.5)
        g = fl[(fl.year == y) & (fl.site == s)]
        crops = sorted(g.crop.unique())
        for ci, crop in enumerate(crops):
            gg = g[g.crop == crop]
            dy = (ci - (len(crops) - 1) / 2) * 0.28
            for _, r in gg.iterrows():
                full, none_ = r.bands_ok == 5, r.bands_ok == 0
                ax.scatter(r.doy + (1.2 if r.stage == "preliminary" else 0), yk + dy, s=34,
                           marker=CROP_MARK[crop],
                           facecolor=YEAR_COL[y] if full else (SURFACE if none_ else YEAR_COL[y] + "66"),
                           edgecolor=YEAR_COL[y], linewidth=1.2, zorder=3)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([f"{s} {y}" for y, s in rows[::-1]])
    ticks = pd.to_datetime(["2000-05-01", "2000-06-01", "2000-07-01", "2000-08-01", "2000-09-01"])
    ax.set_xticks(ticks.dayofyear); ax.set_xticklabels(["1 may", "1 jun", "1 jul", "1 ago", "1 sep"])
    ax.set_xlim(120, 235)
    for sp_ in ("top", "right"):
        ax.spines[sp_].set_visible(False)
    ax.grid(axis="x", color="#e6e5e0", lw=0.6); ax.set_axisbelow(True)
    handles = [Line2D([], [], color=MUTED, lw=1.5, label="siembra"),
               Line2D([], [], marker="o", ls="", mfc=MUTED, mec=MUTED, label="5 bandas"),
               Line2D([], [], marker="o", ls="", mfc=MUTED + "66", mec=MUTED, label="bandas parciales"),
               Line2D([], [], marker="o", ls="", mfc=SURFACE, mec=MUTED, label="archivos vacíos"),
               Line2D([], [], marker="o", ls="", color=MUTED, label="arveja"),
               Line2D([], [], marker="D", ls="", color=MUTED, label="garbanzo"),
               Line2D([], [], marker="s", ls="", color=MUTED, label="mosaico conjunto")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=7, frameon=False, fontsize=6.5)
    ax.set_title("Calendario de vuelos UAV (MicaSense RedEdge) por sitio-año", loc="left", color=INK)
    fig.savefig(OUTDIR / "figS2_flight_calendar.png"); plt.close(fig)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    trials = load_trials()
    fp = fig_sites(trials)
    fp.to_file(OUTDIR / "mosaic_footprints.geojson", driver="GeoJSON")
    fig_location(trials, fp)
    fig_calendar(trials)
    print(fp.drop(columns="geometry").to_string())


if __name__ == "__main__":
    main()
