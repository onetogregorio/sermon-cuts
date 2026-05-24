#!/usr/bin/env python3
"""Minimal Gradio UI for pastors who don't want a terminal.

Three panels stacked top-to-bottom:
  1. Source — paste a YouTube URL or upload an .mp4. "Process" runs the
     Phase A pipeline (ingest → transcribe → VAD → propose input) and
     reports the slug.
  2. Proposed cuts — once cuts_proposed.json exists for the slug, lists
     each cut as a checkbox row with theme + hook + duration. The user
     ticks which ones they want and clicks "Render selected".
  3. Renders — shows the final MP4s with a download button each.

Wraps the existing scripts via subprocess — no logic is duplicated here.
The UI is a thin orchestrator, intentionally.

Usage:
    ui.py [--port 7860]
    pipeline.sh ui              # convenience wrapper
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import fail

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
SCRIPTS = SKILL_ROOT / "scripts"
PIPELINE = SCRIPTS / "pipeline.sh"


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def process_source(source: str, uploaded_file) -> tuple[str, str, list[list]]:
    """Phase A: ingest + transcribe + vad + propose-input. Returns
    (slug, log, list_of_cut_rows_for_table)."""
    if uploaded_file is not None:
        # gradio gives us a temp filepath; pass it straight through.
        source_arg = uploaded_file
    elif source and source.strip():
        source_arg = source.strip()
    else:
        return "", "✗ cole uma URL do YouTube ou faça upload de um .mp4", []

    rc, out, err = _run(["bash", str(PIPELINE), source_arg])
    log = (out + "\n" + err).strip()
    # The orchestrator prints the slug along the way; we recover it by
    # finding which memory/messages/<slug>/ got a transcript.json updated
    # most recently. Cheap and reliable.
    slug = ""
    if MESSAGES.exists():
        candidates = sorted(
            MESSAGES.iterdir(),
            key=lambda p: (
                (p / "transcript.json").stat().st_mtime if (p / "transcript.json").exists() else 0
            ),
            reverse=True,
        )
        if candidates:
            slug = candidates[0].name

    cuts_rows = _load_cuts_for_slug(slug) if slug else []
    return slug, log, cuts_rows


def _load_cuts_for_slug(slug: str) -> list[list]:
    """Read cuts_proposed.json (if the LLM has written it yet) and return
    a list of rows compatible with gradio's Dataframe component: each
    row is [select_bool, n, duration_s, theme, hook]."""
    cuts_file = MESSAGES / slug / "cuts_proposed.json"
    if not cuts_file.exists():
        return []
    cuts = json.loads(cuts_file.read_text())
    rows: list[list] = []
    for cut in cuts:
        n = cut.get("n", len(rows) + 1)
        dur = round(float(cut.get("end", 0)) - float(cut.get("start", 0)), 1)
        theme = (cut.get("theme") or "").strip()
        hook = (cut.get("hook") or "").strip()
        rows.append([False, n, dur, theme, hook])
    return rows


def refresh_cuts(slug: str) -> list[list]:
    """Manual refresh button — re-read cuts_proposed.json for the current
    slug, in case the curator (Claude) has just written it."""
    if not slug:
        return []
    return _load_cuts_for_slug(slug)


def render_selected(slug: str, table_rows: list[list]) -> tuple[str, list[str]]:
    """Run pipeline.sh --render-cuts on the indices the user ticked.
    Returns (log, list_of_output_mp4_paths)."""
    if not slug:
        return "✗ rode 'Process' primeiro pra ter um slug", []
    if not table_rows:
        return "✗ nenhum corte na tabela; rode 'Process' ou 'Refresh cuts'", []

    chosen = [str(row[1]) for row in table_rows if row[0]]
    if not chosen:
        return "✗ marque pelo menos um corte (coluna 'select')", []

    rc, out, err = _run(["bash", str(PIPELINE), "--render-cuts", ",".join(chosen), "--slug", slug])
    log = (out + "\n" + err).strip()

    # Collect final MP4 paths.
    renders_dir = MESSAGES / slug / "renders"
    mp4s = sorted(str(p) for p in renders_dir.glob("*.mp4")) if renders_dir.exists() else []
    return log, mp4s


def build_ui():
    try:
        import gradio as gr
    except ImportError:
        fail(
            "gradio não está instalado",
            hint="rode `pip install gradio` no venv da skill (ou skip esse comando "
            "e use pipeline.sh direto no terminal)",
        )

    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue="amber", neutral_hue="slate"),
        title="Sermon Cuts",
    ) as demo:
        gr.Markdown(
            textwrap.dedent("""
            # Sermon Cuts
            Cola um link de YouTube ou faz upload de um `.mp4` da sua pregação.
            O pipeline transcreve, propõe cortes e renderiza os que você marcar.
            """)
        )

        slug_state = gr.State("")

        with gr.Tab("1. Source"):
            url_in = gr.Textbox(
                label="URL do YouTube",
                placeholder="https://youtube.com/watch?v=...",
            )
            file_in = gr.File(label="ou upload de .mp4 local", file_types=[".mp4", ".mov", ".mkv"])
            process_btn = gr.Button("Process — transcrever + propor cortes", variant="primary")
            slug_out = gr.Textbox(label="slug gerado", interactive=False)
            phase_a_log = gr.Textbox(label="log", lines=10, interactive=False)

        with gr.Tab("2. Proposed cuts"):
            gr.Markdown(
                "Após Process, o Claude lê o transcript e propõe cortes em "
                "`cuts_proposed.json`. Clique **Refresh** depois que isso terminar."
            )
            refresh_btn = gr.Button("Refresh cuts")
            cuts_table = gr.Dataframe(
                headers=["select", "n", "dur (s)", "tema", "hook"],
                datatype=["bool", "number", "number", "str", "str"],
                interactive=True,
                wrap=True,
                label="cortes propostos",
            )
            render_btn = gr.Button("Render selected", variant="primary")

        with gr.Tab("3. Renders"):
            render_log = gr.Textbox(label="log", lines=10, interactive=False)
            output_files = gr.Files(label="cortes renderizados (clique pra baixar)")

        # ── wiring ──
        process_btn.click(
            process_source,
            inputs=[url_in, file_in],
            outputs=[slug_state, phase_a_log, cuts_table],
        ).then(lambda s: s, inputs=slug_state, outputs=slug_out)

        refresh_btn.click(refresh_cuts, inputs=slug_state, outputs=cuts_table)

        render_btn.click(
            render_selected,
            inputs=[slug_state, cuts_table],
            outputs=[render_log, output_files],
        )

    return demo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--share", action="store_true", help="expose via gradio tunnel")
    args = ap.parse_args()

    if not shutil.which("bash") or not PIPELINE.exists():
        fail(
            f"pipeline.sh não encontrado em {PIPELINE}",
            hint="instale a skill primeiro (curl …/install.sh | bash)",
        )

    demo = build_ui()
    demo.launch(server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
