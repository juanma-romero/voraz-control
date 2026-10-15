#!/usr/bin/env python3
"""Genera docs/kanban.md a partir del board Kanban de Hermes.

El board es la fuente de verdad: las tarjetas se crean, mueven y cierran con
`hermes kanban ...` (o desde Hermes). Este script solo lo refleja en un markdown
versionado en git, para leerlo sin abrir el dashboard.

Uso:
    python3 scripts/kanban-md.py            # escribe docs/kanban.md
    python3 scripts/kanban-md.py --check    # falla si el archivo está desactualizado
    python3 scripts/kanban-md.py -o -       # imprime en stdout

Requiere el CLI `hermes` en el PATH.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BOARD = "voraz"
TZ = ZoneInfo("America/Asuncion")
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "kanban.md"

# La línea de timestamp cambia en cada corrida y no debe romper `--check`.
_TS_RE = re.compile(r"^> Última generación: .*$", re.M)


def normalize(md: str) -> str:
    return _TS_RE.sub("> Última generación: <ts>", md)

# Orden de columnas del tablero y cómo se llaman en el markdown.
COLUMNS = [
    ("running", "🔧 En curso"),
    ("review", "👀 En revisión"),
    ("blocked", "🚧 Bloqueado"),
    ("scheduled", "⏰ Agendado"),
    ("ready", "📋 Listo para hacer"),
    ("todo", "📋 Por hacer (esperando dependencias)"),
    ("triage", "💡 Sin definir (ideas)"),
    ("done", "✅ Hecho"),
]

LABEL = dict(COLUMNS)


def fetch(status: str | None = None) -> list[dict]:
    args = ["hermes", "kanban", "--board", BOARD, "ls", "--json", "--sort", "priority-desc"]
    if status:
        args += ["--status", status]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ERROR: falló `{' '.join(args)}`\n{p.stderr}")
    return json.loads(p.stdout or "[]")


def fmt_date(ts: int | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d")


def cell(text: str) -> str:
    """Escapa una celda de tabla markdown."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render(tasks: list[dict]) -> str:
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    by_status: dict[str, list[dict]] = {}
    for t in tasks:
        by_status.setdefault(t["status"], []).append(t)

    open_total = sum(len(v) for k, v in by_status.items() if k != "done")

    out: list[str] = []
    out.append("# Kanban — Voraz")
    out.append("")
    out.append(
        "Tablero de tareas **accionables** y su estado. Complementa a "
        "`backlog.md`, que es el documento de visión, ideas y estado del sistema: "
        "el backlog dice *qué queremos*; este tablero dice *en qué anda cada cosa*."
    )
    out.append("")
    out.append(
        f"> ⚙️ Generado automáticamente por `scripts/kanban-md.py` desde el board "
        f"Kanban de Hermes (`{BOARD}`) — **no editar a mano**.\n"
        f"> Última generación: {now} (hora de Paraguay) · "
        f"{open_total} tarjetas abiertas."
    )
    out.append("")

    # --- Resumen ----------------------------------------------------------
    out.append("## Resumen")
    out.append("")
    out.append("| Estado | Tarjetas |")
    out.append("|---|---:|")
    for key, label in COLUMNS:
        out.append(f"| {label} | {len(by_status.get(key, []))} |")
    out.append(f"| **Total abiertas** | **{open_total}** |")
    out.append("")

    # --- Tablas por columna ----------------------------------------------
    out.append("## Tablero")
    out.append("")
    for key, label in COLUMNS:
        items = by_status.get(key, [])
        if not items:
            continue
        out.append(f"### {label} ({len(items)})")
        out.append("")
        out.append("| ID | P | Tarea | Dueño | Creada |")
        out.append("|---|---:|---|---|---|")
        for t in items:
            owner = t.get("assignee") or "—"
            out.append(
                f"| `{t['id']}` | {t['priority']} | {cell(t['title'])} "
                f"| {cell(owner)} | {fmt_date(t.get('created_at'))} |"
            )
        out.append("")

    # --- Detalle ----------------------------------------------------------
    detail = [t for t in tasks if t["status"] != "done"]
    if detail:
        out.append("## Detalle de las tarjetas abiertas")
        out.append("")
        for key, label in COLUMNS:
            items = [t for t in by_status.get(key, []) if t["status"] != "done"]
            if not items:
                continue
            out.append(f"### {label}")
            out.append("")
            for t in items:
                body = (t.get("body") or "").strip() or "_Sin descripción._"
                out.append(
                    f"<details><summary><code>{t['id']}</code> — "
                    f"{cell(t['title'])}</summary>"
                )
                out.append("")
                out.append(body)
                out.append("")
                if t.get("last_failure_error"):
                    out.append(f"**Último error:** {t['last_failure_error']}")
                    out.append("")
                out.append("</details>")
                out.append("")

    # --- Hecho ------------------------------------------------------------
    done = by_status.get("done", [])
    if done:
        out.append("### ✅ Hecho")
        out.append("")
        for t in sorted(done, key=lambda x: x.get("completed_at") or 0, reverse=True):
            out.append(
                f"- `{t['id']}` **{cell(t['title'])}** — "
                f"cerrada el {fmt_date(t.get('completed_at'))}"
            )
        out.append("")

    # --- Cómo se usa ------------------------------------------------------
    out.append("## Cómo se usa")
    out.append("")
    out.append("El board vive en Hermes (`~/.hermes/kanban/boards/voraz/kanban.db`):")
    out.append("")
    out.append("```bash")
    out.append("hermes kanban --board voraz ls              # ver el tablero en terminal")
    out.append("hermes kanban --board voraz watch           # stream en vivo de eventos")
    out.append("hermes kanban --board voraz show <id>       # detalle de una tarjeta")
    out.append("hermes kanban --board voraz assign <id> default   # darle dueño (la ejecuta el dispatcher)")
    out.append("hermes kanban --board voraz complete <id> <id>    # cerrar tarjetas")
    out.append("hermes dashboard                            # panel web con el tablero")
    out.append("python3 scripts/kanban-md.py                # regenerar este archivo")
    out.append("```")
    out.append("")
    out.append(
        "Una tarjeta **sin dueño** queda visible pero quieta: el dispatcher la "
        "ignora (`Skipped (unassigned)`). Al asignarle un perfil, el dispatcher la "
        "toma y la ejecuta en un workspace aislado, y pasa a *En curso*."
    )
    out.append("")
    out.append(
        "> ⚠️ **La columna «Sin definir (ideas)» es la columna `triage` de Hermes.** "
        "Por eso `kanban.auto_decompose` debe quedar en **`false`**: con ese ajuste "
        "activo, el dispatcher levanta solo las tarjetas de `triage` y las parte en "
        "subtareas asignadas que **empieza a ejecutar sin preguntar**. "
        "Para descomponer una idea a mano y a propósito: "
        "`hermes kanban --board voraz decompose <id>`."
    )
    out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="no escribe; falla si docs/kanban.md está desactualizado")
    ap.add_argument("-o", "--output", default=str(OUT),
                    help="archivo de salida, o '-' para stdout")
    args = ap.parse_args()

    md = render(fetch())

    if args.output == "-":
        print(md, end="")
        return 0

    target = Path(args.output)
    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if normalize(current) != normalize(md):
            print(f"DESACTUALIZADO: {target} — corré `python3 scripts/kanban-md.py`")
            return 1
        print(f"OK: {target} está al día")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    print(f"Escrito {target} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
