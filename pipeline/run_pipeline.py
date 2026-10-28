"""Orquestador: ejecuta los pasos pendientes en secuencia, con progreso y tiempo restante estimado.

Uso:
    python pipeline/run_pipeline.py [--wait-pid PID] [--from 07b] [--no-push]
- Espera opcionalmente a que termine un proceso en curso (p. ej. el registro de la grilla, paso 07).
- Ejecuta cada script, transmite su salida al log en vivo (outputs/pipeline_run.log) y guarda un log por paso
  (outputs/logs/<paso>.log) y un estado JSON (outputs/pipeline_status.json).
- ETA: estimación inicial por paso, recalibrada con la razón real/estimado de los pasos ya terminados.
- Si un paso falla, se detiene (los siguientes dependen de él) y lo informa en el log.
- Tras cada paso exitoso: git add/commit/push de pipeline/, docs/ y outputs/ (salvo --no-push).
Seguimiento en vivo (PowerShell): Get-Content outputs\\pipeline_run.log -Wait -Tail 40
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
LOG = OUT / "pipeline_run.log"
STATUS = OUT / "pipeline_status.json"
STEPS = [  # (id, script, descripción, minutos estimados)
    ("07b", "07b_check_plot_grid.py", "Verificación y refinamiento afín de la grilla", 25),
    ("09", "09_coregistration.py", "Corregistro multitemporal (grilla como referencia)", 6),
    ("10", "10_features.py", "Extracción de rasgos por parcela y fecha", 45),
    ("11", "11_replication.py", "Réplica de Zhang et al. (2021)", 50),
    ("12", "12_temporal.py", "Curvas temporales en grados-día", 10),
    ("13", "13_mixed_models.py", "Modelos mixtos: H², correlaciones, G×E", 30),
    ("14", "14_phenology.py", "Fenología desde el aire", 5),
    ("15", "15_models.py", "Machine Learning / Deep Learning", 120),
    ("16", "16_figures_tables.py", "Figuras y tablas de resultados", 3),
]


def log(msg: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def pid_alive(pid: int) -> bool:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue"],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def git_push(step_id: str, desc: str, minutes: float) -> None:
    cmds = [["git", "add", "pipeline", "docs", "outputs", "README.md", "requirements.txt"],
            ["git", "commit", "-q", "-m", f"Pipeline: paso {step_id} completado - {desc} ({minutes:.0f} min)"],
            ["git", "push", "-q"]]
    for c in cmds:
        r = subprocess.run(c, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
            log(f"   git: {' '.join(c[:2])} → {(r.stderr or r.stdout).strip()[:200]}")
            return
    log(f"   ✓ subido a GitHub (paso {step_id})")


def write_status(state: dict) -> None:
    STATUS.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait-pid", type=int)
    ap.add_argument("--from", dest="start", default=STEPS[0][0])
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    steps = STEPS[[s[0] for s in STEPS].index(a.start):]
    total_est = sum(s[3] for s in steps)
    log("=" * 78)
    log(f"PIPELINE pea_drone · {len(steps)} pasos · estimado {total_est / 60:.1f} h")
    log("   " + " → ".join(s[0] for s in steps))
    if a.wait_pid:
        log(f"Esperando a que termine el proceso {a.wait_pid} (registro de la grilla, paso 07)...")
        t = time.time()
        while pid_alive(a.wait_pid):
            time.sleep(30)
            log(f"   07 sigue en ejecución ({(time.time() - t) / 60:.0f} min de espera)")
        log("   07 terminó.")
        if not a.no_push:
            git_push("07", "Georreferenciación de la grilla", (time.time() - t) / 60)
    state = dict(started=datetime.now(), steps={s[0]: "pendiente" for s in steps})
    ratio, done_est, done_real = 1.0, 0.0, 0.0
    for i, (sid, script, desc, est) in enumerate(steps, 1):
        remaining = sum(s[3] for s in steps[i - 1:]) * ratio
        eta = datetime.now() + timedelta(minutes=remaining)
        log("-" * 78)
        log(f"PASO {i}/{len(steps)} [{sid}] {desc} · estimado {est * ratio:.0f} min · "
            f"restante total ≈ {remaining / 60:.1f} h (fin ≈ {eta:%H:%M})")
        state["steps"][sid] = "en curso"; state["current"] = sid; state["eta"] = eta; write_status(state)
        t0 = time.time()
        with open(OUT / "logs" / f"{sid}.log", "w", encoding="utf-8") as fh:
            p = subprocess.Popen([sys.executable, "-u", "-W", "ignore", str(ROOT / "pipeline" / script)], cwd=ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                 errors="replace", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            for line in p.stdout:
                fh.write(line)
                if line.strip():
                    log(f"   {line.rstrip()[:200]}")
            p.wait()
        mins = (time.time() - t0) / 60
        if p.returncode != 0:
            state["steps"][sid] = f"ERROR (código {p.returncode})"; write_status(state)
            log(f"✗ PASO {sid} FALLÓ tras {mins:.1f} min (ver outputs/logs/{sid}.log). Pipeline detenido.")
            sys.exit(p.returncode)
        done_est += est; done_real += mins
        ratio = max(0.3, min(3.0, done_real / done_est))
        state["steps"][sid] = f"ok ({mins:.1f} min)"; write_status(state)
        log(f"✓ PASO {sid} completado en {mins:.1f} min")
        if not a.no_push:
            git_push(sid, desc, mins)
    log("=" * 78)
    log(f"PIPELINE COMPLETO en {(time.time() - state['started'].timestamp()) / 3600:.1f} h")
    state["finished"] = datetime.now(); write_status(state)


if __name__ == "__main__":
    main()
