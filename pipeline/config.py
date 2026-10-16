"""Configuración común y parseo de rutas del dataset UAV de leguminosas (WSU/USDA-ARS, 2017-2019).

Todas las rutas se resuelven relativas a la raíz del proyecto (carpeta `drone_images`).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
EXCEL = {y: ROOT / f"{y}PulseDataset.xlsx" for y in (2017, 2018, 2019)}
PLOT_MAPS_PDF = ROOT / "PulsePlotMaps_2017-2019.pdf"

# MicaSense RedEdge (Zhang et al., 2021): centro ± semiancho de banda (nm)
BANDS = {
    "blue": (475, 10),
    "green": (560, 10),
    "red": (668, 5),
    "red edge": (717, 5),
    "nir": (840, 20),
}
BAND_ORDER = ["blue", "green", "red", "red edge", "nir"]

MONTHS = {"jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8}
SITES = ("Pullman", "Fairfield", "Genesee")


def parse_tif(path: Path) -> dict:
    """Extrae año, sitio, cultivo, fecha, ensayo (advanced/preliminary) y banda de la ruta de un .tif."""
    rel = path.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    year = int(parts[0].replace("Images", ""))
    site = next(s for s in SITES if parts[1].startswith(s))
    flight_dir = parts[-2]  # carpeta más interna = vuelo
    band = re.search(r"mosaic_(blue|green|red edge|red|nir)\.tif$", path.name).group(1)

    low = flight_dir.lower()
    if "pea_chickpea" in low or "pea-chickpea" in low:
        crop = "pea+chickpea"
    elif "chickpea" in low:
        crop = "chickpea"
    elif "pea" in low:
        crop = "pea"
    else:
        crop = "unknown"
    stage = "preliminary" if "prelim" in low else ("advanced" if "advanced" in low else "")

    m = re.search(r"(jun(?:e)?|jul(?:y)?|aug)[ _]?(\d{1,2})", low)
    month, day = MONTHS[m.group(1)], int(m.group(2))
    # La carpeta 'Preliminary_July16' contiene archivos rotulados 'Jun16'; la fecha real es 7/17/2019
    # según la hoja Description (vuelo de preliminares: 6/17, 7/5, 7/17).
    if year == 2019 and stage == "preliminary" and month == 7 and day == 16:
        day = 17
    flight_date = date(year, month, day)

    return dict(path=rel, year=year, site=site, crop=crop, stage=stage,
                flight_dir=flight_dir, date=flight_date.isoformat(), band=band)
