#!/usr/bin/env python3
"""Interactive review TUI for proposed cuts.

Reads ``cuts_proposed.json`` for a slug and shows each cut as a row with
theme, hook, duration, and coherence score. Navigate with ↑/↓, toggle a
cut with SPACE, render the marked ones with ENTER, quit with q.

Avoids any third-party dep — uses stdlib ``curses`` so the install
surface stays small. The default Apple/Linux Python ship with it.

Usage:
    review.py <slug>
    pipeline.sh review <slug>      # convenience wrapper

On ENTER, exits with the render command printed to stdout so the wrapper
shell can pick it up:
    ./scripts/pipeline.sh --render-cuts 1,3,4,7 --slug <slug>
"""

from __future__ import annotations

import argparse
import curses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import fail, repo_root, resolve_messages_dir

MESSAGES = resolve_messages_dir()


def _truncate(text: str, width: int) -> str:
    """Cut a string to ``width`` cells, adding an ellipsis if it overflows."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def _draw(stdscr, slug: str, cuts: list[dict], cursor: int, marked: set[int]) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    # ─── header ─────────────────────────────────────────────────────────
    title = f"sermon-cuts review  ·  {slug}  ·  {len(cuts)} cortes propostos"
    stdscr.addstr(0, 0, _truncate(title, width - 1), curses.A_BOLD)
    help_line = "↑↓ navegar   SPACE marcar   ENTER renderizar marcados   q sair"
    stdscr.addstr(1, 0, _truncate(help_line, width - 1), curses.A_DIM)
    stdscr.addstr(2, 0, "─" * (width - 1))

    # ─── list ──────────────────────────────────────────────────────────
    # Reserve top 3 lines (title + help + separator) and bottom 4 (detail + footer).
    list_top = 3
    list_height = max(1, height - list_top - 6)
    visible_start = max(0, min(cursor - list_height // 2, len(cuts) - list_height))
    visible_start = max(0, visible_start)
    for offset, idx in enumerate(range(visible_start, min(len(cuts), visible_start + list_height))):
        cut = cuts[idx]
        n = cut.get("n", idx + 1)
        mark = "■" if idx in marked else "·"
        theme = (cut.get("theme") or "").strip() or "(sem tema)"
        dur = _fmt_duration(float(cut.get("end", 0)) - float(cut.get("start", 0)))
        score = cut.get("coherence_score")
        score_str = f"{score:.1f}" if isinstance(score, int | float) else "?  "

        prefix = f"{mark} {n:>2}  {dur:>4}  {score_str:>4}  "
        room = max(20, width - len(prefix) - 2)
        row = f"{prefix}{_truncate(theme, room)}"

        attr = curses.A_REVERSE if idx == cursor else curses.A_NORMAL
        if idx in marked:
            attr |= curses.A_BOLD
        try:
            stdscr.addstr(list_top + offset, 0, row, attr)
        except curses.error:
            # Terminal is narrower than the row — addstr at the bottom-right
            # cell raises. Safe to swallow; the truncation above already
            # tries to keep us within bounds.
            pass

    # ─── detail panel (hook of the current cut) ─────────────────────────
    if 0 <= cursor < len(cuts):
        cut = cuts[cursor]
        hook = (cut.get("hook") or "(sem hook)").strip()
        conclusion = (cut.get("conclusion") or "").strip()
        slug_label = cut.get("slug", "")
        detail_y = height - 4
        stdscr.addstr(detail_y, 0, "─" * (width - 1))
        stdscr.addstr(detail_y + 1, 0, _truncate(f"slug: {slug_label}", width - 1), curses.A_DIM)
        stdscr.addstr(detail_y + 2, 0, _truncate(f"hook: {hook}", width - 1))
        if conclusion:
            stdscr.addstr(detail_y + 3, 0, _truncate(f"end: {conclusion}", width - 1), curses.A_DIM)

    stdscr.refresh()


def _run_curses(stdscr, slug: str, cuts: list[dict]) -> list[int] | None:
    curses.curs_set(0)
    stdscr.keypad(True)
    cursor = 0
    marked: set[int] = set()
    # Pre-mark cuts the curator already approved in JSON (forward-compat).
    for i, cut in enumerate(cuts):
        if cut.get("approved"):
            marked.add(i)

    while True:
        _draw(stdscr, slug, cuts, cursor, marked)
        ch = stdscr.getch()
        if ch in (ord("q"), ord("Q"), 27):  # 27 = ESC
            return None
        if ch in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(cuts) - 1, cursor + 1)
        elif ch in (curses.KEY_HOME, ord("g")):
            cursor = 0
        elif ch in (curses.KEY_END, ord("G")):
            cursor = len(cuts) - 1
        elif ch == ord(" "):
            if cursor in marked:
                marked.remove(cursor)
            else:
                marked.add(cursor)
        elif ch in (ord("a"), ord("A")):
            # toggle-all
            if len(marked) == len(cuts):
                marked.clear()
            else:
                marked = set(range(len(cuts)))
        elif ch in (curses.KEY_ENTER, 10, 13):
            return sorted(marked)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the chosen cut indices and exit instead of starting curses",
    )
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    cuts_file = msg_dir / "cuts_proposed.json"
    if not cuts_file.exists():
        fail(
            f"cuts_proposed.json não encontrado em {msg_dir}",
            hint="rode a fase A primeiro (pipeline.sh <source>) e peça pro Claude propor cortes",
        )
    cuts = json.loads(cuts_file.read_text())
    if not cuts:
        fail(
            f"{cuts_file} está vazio",
            hint="o LLM ainda não escreveu cortes propostos — rode propose_cuts.md",
        )

    if args.dry_run:
        for i, cut in enumerate(cuts):
            theme = (cut.get("theme") or "")[:60]
            print(f"  {i + 1:>2}  {theme}")
        return

    indices = curses.wrapper(_run_curses, args.slug, cuts)
    if indices is None:
        print("(cancelado — nenhum corte renderizado)", file=sys.stderr)
        sys.exit(2)
    if not indices:
        print("(nada marcado — nenhum corte renderizado)", file=sys.stderr)
        sys.exit(2)

    # Convert 0-based list indices to 1-based cut indices that pipeline.sh
    # expects (--render-cuts uses 1-based to match the human-readable JSON
    # numbering shown by --dry-run).
    chosen = [str(i + 1) for i in indices]
    cmd = f"{repo_root()}/scripts/pipeline.sh --render-cuts {','.join(chosen)} --slug {args.slug}"
    print(cmd)


if __name__ == "__main__":
    main()
