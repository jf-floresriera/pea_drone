"""Fase 2.4a - Digitalización de los croquis de parcelas (PulsePlotMaps_2017-2019.pdf).

Cada página es una matriz fila × columna dibujada sobre el mosaico. Cada celda tiene el número de parcela sobre un
rectángulo coloreado; el color identifica el ensayo (las etiquetas laterales "1801", "1803"... llevan el mismo color).
Se extraen las palabras con su posición y los rectángulos vectoriales con su color de relleno:
  celda → color del rectángulo más pequeño que contiene la palabra → ensayo (por color de las etiquetas).
La fila y la columna se obtienen agrupando las coordenadas de las celdas.
Tokens no numéricos: a/b/e = bordes, c = relleno (check o filler), d = descarte, NA = vacío.

Validación: para cada ensayo, el conjunto de números de parcela del croquis debe coincidir con el del Excel.
Se corrigen los errores de digitación conocidos (docs/DATA_ISSUES.md, MAP-01) y se reportan los demás.
Salidas: outputs/06_plot_maps/{plot_map_cells.csv, plot_map_validation.csv, maps/<pagina>.png}
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from config import OUT, PLOT_MAPS_PDF  # noqa: E402

OUTDIR = OUT / "06_plot_maps"
# Página (1-based) → sitio-año-campo. La pág. 1 no tiene título: por sus ensayos (1701/1701B/1702, 120+57+63
# parcelas) es Fairfield 2017. La pág. 10 tampoco: contiene 1981 → garbanzo Fairfield 2019 (campo separado).
PAGES = {
    1: (2017, "Fairfield", "pea"), 2: (2017, "Pullman", "pea"), 3: (2017, "Pullman", "chickpea"),
    4: (2018, "Fairfield", "pea"), 5: (2018, "Fairfield", "chickpea"), 6: (2018, "Genesee", "pea+chickpea"),
    7: (2018, "Pullman", "pea"), 8: (2018, "Pullman", "chickpea"), 9: (2019, "Fairfield", "pea"),
    10: (2019, "Fairfield", "chickpea"), 11: (2019, "Genesee", "pea+chickpea"),
    12: (2019, "Pullman", "advanced"), 13: (2019, "Pullman", "preliminary"),
}
TRIAL_RE = re.compile(r"^(1[789]\d{2}[BG]?)$")
CELL_RE = re.compile(r"^(\d{1,3}|[abcde]|NA)$")


def color_key(c) -> tuple:
    return tuple(round(float(v), 2) for v in c)


def cluster_1d(vals: np.ndarray, tol: float) -> np.ndarray:
    """Agrupa coordenadas en filas/columnas; devuelve el índice de grupo ordenado."""
    order = np.argsort(vals)
    labels = np.empty(len(vals), int)
    g, last = 0, None
    for i in order:
        if last is not None and vals[i] - last > tol:
            g += 1
        labels[i] = g
        last = vals[i]
    return labels


def parse_page(page, pno: int) -> pd.DataFrame:
    rects = [(fz_rect, color_key(d["fill"])) for d in page.get_drawings() if d.get("fill")
             for fz_rect in [d["rect"]] if fz_rect.width < 120 and fz_rect.height < 40]
    words = page.get_text("words")

    def fill_at(x, y):
        best = None
        for r, c in rects:
            if r.x0 <= x <= r.x1 and r.y0 <= y <= r.y1 and c not in ((1.0, 1.0, 1.0), (0.91, 0.92, 0.96)):
                if best is None or r.width * r.height < best[0]:
                    best = (r.width * r.height, c, r)
        return best

    # Etiquetas de ensayo: palabra con código de ensayo sobre un rectángulo coloreado
    label_col = {}
    for w in words:
        if TRIAL_RE.match(w[4]):
            f = fill_at((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            if f:
                label_col.setdefault(f[1], set()).add(w[4])
    # Celdas: tokens sobre rectángulo coloreado, excluyendo encabezados ("Col", "Row") y etiquetas
    hdr_y = [w[3] for w in words if w[4] == "Col"]
    y_min = max(hdr_y) if hdr_y else -1
    # Números que siguen a "Row"/"Col" en la misma línea son etiquetas, no celdas
    lbl_idx = {(w[5], w[6], w[7] + 1) for w in words if w[4] in ("Row", "Col")}
    cells = []
    for w in words:
        tok = w[4]
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        f = fill_at(cx, cy)
        # Un código de ensayo escrito DENTRO de una celda (rectángulo angosto) es un error de digitación del croquis
        in_cell_code = bool(TRIAL_RE.match(tok)) and f is not None and f[2].width < 30
        if in_cell_code:
            tok = f"?{tok}"
        elif not CELL_RE.match(tok) or TRIAL_RE.match(tok) or (w[5], w[6], w[7]) in lbl_idx:
            continue
        if cy <= y_min or f is None:
            continue
        cells.append(dict(page=pno, token=tok, x=cx, y=cy, fill=f[1], cw=f[2].width, ch=f[2].height))
    df = pd.DataFrame(cells)
    if df.empty:
        return df
    df["kind_hint"] = np.where(df.token.str.fullmatch(r"\d+|\?.*"), "plot", "other")
    # Las etiquetas "Row k" y "Border" no son celdas; quitar celdas en columnas de etiquetas (x fuera de la matriz)
    row_lbl_x = [w[2] for w in words if w[4] in ("Row", "Border", "Blank") and w[0] < page.rect.width * 0.45]
    if row_lbl_x:
        df = df[df.x > max(row_lbl_x)]
    tol_y = np.median(df.ch) * 0.6
    tol_x = np.median(df.cw) * 1.2
    df["map_row"] = cluster_1d(df.y.to_numpy(), tol_y) + 1
    df["map_col"] = cluster_1d(df.x.to_numpy(), tol_x) + 1
    # Ensayo por color
    col2trial = {c: sorted(v) for c, v in label_col.items()}
    df["trial_label"] = df.fill.map(lambda c: ",".join(col2trial.get(c, [])))
    return df


def assign_trials(df: pd.DataFrame, year: int, site: str, plots: pd.DataFrame) -> pd.DataFrame:
    """Resuelve colores sin etiqueta o con varias etiquetas usando los números de parcela del Excel."""
    trials = plots[(plots.year == year) & (plots.site == site)]
    sets = {t: set(g["plot"].astype(int)) for t, g in trials.groupby("trial")}
    out = []
    labelled = {f for f, g in df.groupby("fill") if g.trial_label.iloc[0]}
    for fill, g in df.groupby("fill"):
        if fill not in labelled and (g.kind_hint == "plot").any() and len(g) <= 5:
            # Color sin etiqueta (p. ej. celdas resaltadas por los autores): ensayo mayoritario de su(s) fila(s)
            same_rows = df[df.map_row.isin(g.map_row) & df.fill.isin(labelled)]
            if not same_rows.empty:
                lab_fill = same_rows.fill.mode().iloc[0]
                t = df[df.fill == lab_fill].trial_label.iloc[0].split(",")
                if len(t) == 1:
                    out.append(g.assign(trial=t[0]))
                    continue
        nums = set(g.token[g.token.str.isdigit()].astype(int))
        lab = [t for t in g.trial_label.iloc[0].split(",") if t]
        cands = [t for t in (lab or sets) if t in sets]
        if not nums:
            t = lab[0] if len(lab) == 1 else ""
        else:
            # ensayo cuyo conjunto de parcelas mejor cubre los números de este color (Jaccard)
            t = max(cands, key=lambda k: len(nums & sets[k]) / len(nums | sets[k])) if cands else ""
        out.append(g.assign(trial=t))
    return pd.concat(out)


# Nota: en Fairfield 2019 (pág. 9) la fila 2 de 1901 dice 12, 22, 2 y está resaltada en VERDE por los autores
# (posición de siembra anotada). Se respeta el croquis tal cual (decisión: confiar en los datos de los investigadores).
# Correcciones de digitación del croquis (docs/DATA_ISSUES.md, MAP-01). Clave: (página, fila, columna, token leído)
# → token corregido. Cada corrección se verifica por la secuencia de numeración de la columna y el Excel.
CORRECTIONS = {
    (4, 16, 5, "36"): "35",      # Fairfield 2018, 1802: columna 5 = 32, 33, 34, [35], 36…
    (7, 2, 6, "35"): "55",       # Pullman 2018, 1801: columna 6 = [55], 56, 57…
    (5, None, None, "?1881"): "32",   # Fairfield 2018, 1881: la celda de la parcela 32 dice "1881"
    (8, None, None, "?1881"): "32",   # Pullman 2018, 1881: ídem
}


def apply_corrections(df: pd.DataFrame, pno: int) -> pd.DataFrame:
    df = df.copy()
    df["corrected_from"] = ""
    for (pg, r, c, old), new in CORRECTIONS.items():
        if pg != pno:
            continue
        m = df.token.eq(old)
        if r is not None:
            m &= df.map_row.eq(r) & df.map_col.eq(c)
        assert m.sum() == 1, f"corrección no aplicable: pág {pg} fila {r} col {c} '{old}' ({m.sum()} coincidencias)"
        df.loc[m, "corrected_from"] = old
        df.loc[m, "token"] = new
    return df


def main() -> None:
    (OUTDIR / "maps").mkdir(parents=True, exist_ok=True)
    plots = pd.read_csv(OUT / "02_tabular_qc" / "plots_master.csv", dtype={"trial": str})
    doc = pymupdf.open(PLOT_MAPS_PDF)
    allc, val = [], []
    for i, page in enumerate(doc, 1):
        year, site, field = PAGES[i]
        page.get_pixmap(dpi=110).save(OUTDIR / "maps" / f"p{i:02d}_{year}_{site}_{field}.png")
        df = apply_corrections(parse_page(page, i), i)
        df = assign_trials(df, year, site, plots)
        df.insert(1, "year", year); df.insert(2, "site", site); df.insert(3, "field", field)
        df["plot"] = pd.to_numeric(df.token, errors="coerce").astype("Int64")
        df["kind"] = np.where(df["plot"].notna(), "plot",
                              df.token.map({"a": "border", "b": "border", "e": "border", "c": "filler",
                                            "d": "discard", "NA": "empty"}))
        allc.append(df)
        for t, g in df[df.kind == "plot"].groupby("trial"):
            got = g["plot"].astype(int)
            exp = set(plots[(plots.year == year) & (plots.site == site) & (plots.trial == t)]["plot"].astype(int))
            dup = sorted(got[got.duplicated()].unique().tolist())
            val.append(dict(page=i, year=year, site=site, field=field, trial=t, n_map=len(got), n_excel=len(exp),
                            missing_in_map=sorted(exp - set(got))[:20], extra_in_map=sorted(set(got) - exp)[:20],
                            duplicated=dup, n_rows=g.map_row.nunique(), n_cols=g.map_col.nunique()))
    cells = pd.concat(allc, ignore_index=True)
    cells.drop(columns=["fill"]).to_csv(OUTDIR / "plot_map_cells.csv", index=False)
    v = pd.DataFrame(val)
    v.to_csv(OUTDIR / "plot_map_validation.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
    print(v.to_string())


if __name__ == "__main__":
    main()
