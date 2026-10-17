"""Estilo gráfico común para todas las figuras del manuscrito.

Reglas (aplicadas en todos los scripts de resultados):
- Una sola tipografía (DejaVu Sans), tamaños fijos: 8 pt texto, 7 pt ejes, 6 pt notas.
- Paleta categórica validada (orden fijo, nunca cíclica): años, cultivos y clases comerciales usan siempre el mismo color.
- Secuencial = un solo tono; divergente = dos tonos con gris neutro en el centro (correlaciones).
- `constrained_layout` en todas las figuras; leyendas fuera del área de datos; etiquetas largas se envuelven.
- Anchos de figura de revista: 1 columna = 3,5 in, 1,5 columnas = 5,5 in, 2 columnas = 7,2 in. Exportación a 300 dpi
  en PNG y PDF.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
YEAR = {2017: CAT[0], 2018: CAT[1], 2019: CAT[2]}
CROP = {"pea": CAT[0], "chickpea": CAT[1]}
MARKET = {"green_pea": CAT[2], "yellow_pea": CAT[3], "nz_green_yellow_pea": CAT[4], "kabuli_chickpea": CAT[1],
          "green_chickpea": CAT[6]}
MARKET_ES = {"green_pea": "Arveja verde", "yellow_pea": "Arveja amarilla", "nz_green_yellow_pea": "Arveja verde-amarilla NZ",
             "kabuli_chickpea": "Garbanzo kabuli", "green_chickpea": "Garbanzo verde"}
SCHEME = {"parcela": CAT[0], "genotipo": CAT[1], "ambiente": CAT[2], "año futuro": CAT[6]}
SEQ = LinearSegmentedColormap.from_list("seq", ["#f2f6fc", "#2a78d6", "#0b2f5c"])
DIV = LinearSegmentedColormap.from_list("div", ["#e34948", "#f3d6d6", "#ecebe8", "#d6e4f6", "#2a78d6"])
WIDTH = {"1col": 3.5, "1.5col": 5.5, "2col": 7.2}


def setup() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 7.5,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "legend.title_fontsize": 7,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "text.color": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "grid.color": GRID, "grid.linewidth": 0.6, "lines.linewidth": 1.6, "lines.markersize": 4,
        "legend.frameon": False, "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
        "figure.constrained_layout.use": True, "axes.titlelocation": "left", "axes.titleweight": "bold",
    })


def figure(width: str = "2col", height: float = 3.0, **kw):
    setup()
    return plt.subplots(figsize=(WIDTH[width], height), **kw)


def wrap(label: str, width: int = 18) -> str:
    return "\n".join(textwrap.wrap(str(label), width)) or str(label)


def panel_label(ax, letter: str) -> None:
    ax.set_title(f"({letter})", loc="left", fontweight="bold", fontsize=8, pad=4)


def note(fig, text: str) -> None:
    """Nota al pie fuera del área de ejes (no se superpone con etiquetas)."""
    fig.supxlabel("\n".join(textwrap.wrap(text, 160)), fontsize=6, color=MUTED, x=0.0, ha="left")


def market_legend(fig, classes=None, loc="outside upper center", ncol=5) -> None:
    """Leyenda única de clases comerciales (parches de color) fuera de los ejes, para no rotular cada eje x."""
    import matplotlib.patches as mpatches
    classes = classes or list(MARKET)
    handles = [mpatches.Patch(facecolor=MARKET[c], alpha=0.6, edgecolor=MUTED, label=MARKET_ES[c]) for c in classes]
    fig.legend(handles=handles, loc=loc, ncol=ncol, frameon=False)


def save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
