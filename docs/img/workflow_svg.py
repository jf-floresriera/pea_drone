"""Genera docs/img/workflow.svg: diagrama de flujo animado del pipeline (sin emojis)."""
import sys
from xml.sax.saxutils import escape as e

out = sys.argv[1]
W, H = 1200, 640
phases = [
    ("1", "Datos y calidad", "#58a6ff", [
        ("01", "Inventario de imágenes", "275 ortomosaicos, 55 vuelos"),
        ("02", "Revisión de datos de campo", "2415 parcelas, 34 ensayos"),
        ("03", "Respuesta espectral", "DN, no reflectancia"),
        ("04", "Mapas de contexto", "sitios y calendario")]),
    ("2", "Geomática", "#3fb950", [
        ("05", "Calibración con Sentinel-2", "442 sectores de 20 m"),
        ("06", "Digitalización de croquis", "34/34 ensayos validados"),
        ("07", "Georreferenciar la grilla", "12 lotes, refinamiento afín"),
        ("09", "Corregistro entre fechas", "desfase mediano 0,68 m")]),
    ("3", "Rasgos por parcela", "#d29922", [
        ("08", "Clima y grados-día", "Daymet V4, base 3 °C"),
        ("10", "Máscara de dosel", "Otsu sobre SAVI calibrado"),
        ("10", "Índices y textura", "11 índices + GLCM por parcela"),
        ("10", "Rasgos por vuelo", "8079 registros")]),
    ("4", "Réplica y análisis", "#bc8cff", [
        ("11", "Réplica de Zhang et al.", "correlación y LASSO"),
        ("12", "Curvas en grados-día", "crecimiento y senescencia"),
        ("13", "Modelos mixtos", "H², correlación genética, G×E"),
        ("14", "Fenología", "floración y madurez")]),
    ("5", "Modelos y resultados", "#f78166", [
        ("15", "Aprendizaje automático", "6 modelos × 4 validaciones"),
        ("15b", "Reflectancia absoluta", "transferencia entre ambientes"),
        ("16", "Figuras y tablas", "22 figuras, 5 tablas"),
        ("run", "Orquestador del pipeline", "ejecuta 07b → 16 con log")]),
]
inputs = ["Ortomosaicos UAV", "Datos de campo", "Croquis PDF", "Sentinel-2 L2A", "Daymet V4"]

CW, GAP, X0, TOP = 210, 22, 30, 150
BH, BG = 74, 14
CYC = 10  # segundos por ciclo
s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Flujo de trabajo del pipeline pea_drone en cinco fases">')
s.append('''<defs>
<linearGradient id="bgw" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#10231a"/></linearGradient>
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#8b949e"/></marker>
</defs>''')
css = [
    ".h{font:700 22px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#f0f6fc}",
    ".sh{font:400 14px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#8b949e}",
    ".pt{font:700 15px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#f0f6fc}",
    ".pn{font:700 13px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#0d1117}",
    ".bn{font:600 13px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#e6edf3}",
    ".bd{font:400 11.5px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#8b949e}",
    ".code{font:700 11px 'Consolas','SFMono-Regular',Menlo,monospace}",
    ".in{font:600 12px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#c9d1d9}",
    ".flow{stroke-dasharray:6 6;animation:dash 1s linear infinite}",
    "@keyframes dash{to{stroke-dashoffset:-12}}",
    f"@keyframes glow{{0%,24%,100%{{opacity:0}}4%,18%{{opacity:1}}}}",
    f"@keyframes dot{{from{{transform:translateX(0)}}to{{transform:translateX({W-2*X0-20}px)}}}}",
    f".dot{{animation:dot {CYC}s linear infinite}}",
]
for i in range(5):
    css.append(f".g{i}{{opacity:0;animation:glow {CYC}s ease-in-out infinite {i*CYC/5:.1f}s}}")
s.append("<style>" + "".join(css) + "</style>")
s.append(f'<rect width="{W}" height="{H}" rx="14" fill="url(#bgw)"/>')
s.append(f'<text x="{X0}" y="44" class="h">Flujo de trabajo reproducible</text>')
s.append(f'<text x="{X0}" y="68" class="sh">16 programas numerados en pipeline/ · cada paso guarda sus resultados en outputs/NN_*/</text>')

# entradas
iw = (W - 2 * X0 - 4 * 12) / 5
for k, name in enumerate(inputs):
    x = X0 + k * (iw + 12)
    s.append(f'<rect x="{x:.0f}" y="86" width="{iw:.0f}" height="30" rx="15" fill="#161b22" stroke="#30363d"/>')
    s.append(f'<text x="{x+iw/2:.0f}" y="106" text-anchor="middle" class="in">{e(name)}</text>')
s.append(f'<text x="{W/2}" y="136" text-anchor="middle" class="sh" style="font-size:11px">datos de entrada</text>')

colH = 52 + 4 * (BH + BG)
for i, (num, title, col, boxes) in enumerate(phases):
    x = X0 + i * (CW + GAP)
    # tarjeta
    s.append(f'<rect x="{x}" y="{TOP}" width="{CW}" height="{colH}" rx="12" fill="#161b22" stroke="#30363d"/>')
    s.append(f'<rect class="g{i}" x="{x-1}" y="{TOP-1}" width="{CW+2}" height="{colH+2}" rx="13" fill="none" '
             f'stroke="{col}" stroke-width="2.5"/>')
    s.append(f'<rect x="{x}" y="{TOP}" width="{CW}" height="40" rx="12" fill="{col}" fill-opacity="0.14"/>')
    s.append(f'<circle cx="{x+22}" cy="{TOP+20}" r="11" fill="{col}"/>')
    s.append(f'<text x="{x+22}" y="{TOP+25}" text-anchor="middle" class="pn">{num}</text>')
    s.append(f'<text x="{x+40}" y="{TOP+25}" class="pt">{e(title)}</text>')
    prev = None
    for j, (code, name, desc) in enumerate(boxes):
        if not code:
            continue
        by = TOP + 52 + j * (BH + BG)
        s.append(f'<rect x="{x+12}" y="{by}" width="{CW-24}" height="{BH}" rx="8" fill="#0d1117" stroke="#30363d"/>')
        s.append(f'<rect x="{x+12}" y="{by}" width="4" height="{BH}" rx="2" fill="{col}"/>')
        s.append(f'<text x="{x+26}" y="{by+22}" class="code" fill="{col}" style="fill:{col}">{e(code)}</text>')
        s.append(f'<text x="{x+26}" y="{by+42}" class="bn">{e(name)}</text>')
        s.append(f'<text x="{x+26}" y="{by+61}" class="bd">{e(desc)}</text>')
        if prev is not None:
            cx = x + CW / 2
            s.append(f'<line x1="{cx}" y1="{prev}" x2="{cx}" y2="{by-2}" stroke="#8b949e" stroke-width="1.5" '
                     f'class="flow" marker-end="url(#ar)"/>')
        prev = by + BH
    # conector a la siguiente fase
    if i < 4:
        y = TOP + colH / 2
        s.append(f'<line x1="{x+CW+2}" y1="{y}" x2="{x+CW+GAP-3}" y2="{y}" stroke="{col}" stroke-width="3" '
                 f'class="flow" marker-end="url(#ar)"/>')

# línea de progreso con punto animado
ly = TOP + colH + 30
s.append(f'<line x1="{X0+10}" y1="{ly}" x2="{W-X0-10}" y2="{ly}" stroke="#30363d" stroke-width="4" stroke-linecap="round"/>')
s.append(f'<g class="dot"><circle cx="{X0+10}" cy="{ly}" r="7" fill="#3fb950"/><circle cx="{X0+10}" cy="{ly}" r="12" '
         f'fill="#3fb950" fill-opacity="0.25"/></g>')
s.append(f'<text x="{X0+10}" y="{ly+26}" class="sh" style="font-size:12px">imágenes y datos crudos</text>')
s.append(f'<text x="{W-X0-10}" y="{ly+26}" text-anchor="end" class="sh" style="font-size:12px">'
         f'rasgos, parámetros genéticos, modelos y figuras</text>')
s.append("</svg>")
open(out, "w", encoding="utf-8").write("\n".join(s))
print("alto usado:", ly + 40, "de", H)
