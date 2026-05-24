#!/usr/bin/env python3
"""Nightly automation for sermon-cuts.

Watches a YouTube channel (or any yt-dlp-compatible source) for the
latest video that hasn't been processed yet, runs Phase A (ingest →
transcribe → VAD → propose-input), and POSTs a summary to a webhook
URL (Discord, Slack, Telegram bot, generic HTTP) so the curator can
review the proposals from wherever.

Intentionally does NOT render anything — the human still curates which
cuts ship. The job here is: "wake me up when a new sermon is ready to
review".

Designed for cron / launchd / systemd-timer:

    0 6 * * *  cd ~/.claude/skills/sermon-cuts && \\
               ./scripts/pipeline.sh nightly \\
                 --channel https://youtube.com/@my_channel \\
                 --webhook https://discord.com/api/webhooks/...

State is kept in ``memory/.nightly_state.json`` so the second wake-up
doesn't reprocess the same video.

Usage:
    nightly.py --channel <url> [--webhook <url>] [--max-videos 1] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import fail, repo_root, resolve_messages_dir, warn

MESSAGES = resolve_messages_dir()
# Nightly state file sits next to the messages dir (same lifetime: when
# you blow away the messages folder you forget what nightly has seen).
STATE_FILE = MESSAGES.parent / ".nightly_state.json"
PIPELINE = repo_root() / "scripts/pipeline.sh"


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_video_ids": []}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _list_recent_videos(channel_url: str, max_n: int) -> list[dict]:
    """Use yt-dlp to enumerate the channel's most recent videos without
    downloading them. Returns a list of {id, title, url, duration, upload_date}."""
    proc = subprocess.run(
        [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--playlist-end",
            str(max_n),
            "--no-warnings",
            channel_url,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(
            f"yt-dlp falhou pra listar {channel_url}",
            hint=f"saída: {proc.stderr[-400:]}",
        )
    videos: list[dict] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        meta = json.loads(line)
        videos.append(
            {
                "id": meta.get("id"),
                "title": meta.get("title"),
                "url": meta.get("url") or f"https://youtube.com/watch?v={meta.get('id')}",
                "duration": meta.get("duration"),
                "upload_date": meta.get("upload_date"),
            }
        )
    return videos


def _post_webhook(webhook_url: str, payload: dict) -> None:
    """POST JSON to ``webhook_url``. Best-effort: failures log a warning
    but don't abort the rest of the run."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except urllib.error.URLError as e:
        warn(f"webhook falhou: {e}")


def _build_webhook_payload(slug: str, video: dict) -> dict:
    """Build a Discord/Slack-friendly payload. Most webhook services accept
    a plain ``content`` field; the rich embed is a Discord nicety that
    other endpoints ignore harmlessly."""
    n_cuts_file = MESSAGES / slug / "cuts_proposed.json"
    n_cuts = (
        len(json.loads(n_cuts_file.read_text()))
        if n_cuts_file.exists()
        else "(LLM ainda não escreveu cuts_proposed.json)"
    )
    cuts_path = MESSAGES / slug / "cuts_proposed.json"
    msg = (
        f"📼 **Novo sermão pronto pra revisar** — `{slug}`\n"
        f"• Título: {video.get('title')}\n"
        f"• Duração: {video.get('duration', 0) // 60} min\n"
        f"• Cortes propostos: {n_cuts}\n"
        f"• Revisar: `./scripts/pipeline.sh review {slug}`\n"
        f"• JSON em: `{cuts_path}`"
    )
    return {
        "content": msg,
        "embeds": [
            {
                "title": video.get("title", "video"),
                "url": video.get("url"),
                "description": f"slug: `{slug}`",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, help="YouTube channel URL or playlist")
    ap.add_argument("--webhook", help="POST a summary JSON to this URL on success")
    ap.add_argument(
        "--max-videos",
        type=int,
        default=1,
        help="how many of the channel's most recent videos to consider (default 1)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would happen without ingesting / posting",
    )
    args = ap.parse_args()

    state = _load_state()
    seen: set[str] = set(state.get("seen_video_ids", []))

    print(f"[nightly] checking {args.channel} (last {args.max_videos})", file=sys.stderr)
    videos = _list_recent_videos(args.channel, args.max_videos)
    new_videos = [v for v in videos if v.get("id") and v["id"] not in seen]
    if not new_videos:
        print(json.dumps({"ok": True, "skipped": True, "reason": "no new videos"}, indent=2))
        return

    processed: list[str] = []
    for video in new_videos:
        print(f"[nightly] new video: {video['title']} ({video['url']})", file=sys.stderr)
        if args.dry_run:
            processed.append(video["id"])
            continue

        # Phase A only — ingest + transcribe + VAD + propose-input.
        proc = subprocess.run(["bash", str(PIPELINE), video["url"]])
        if proc.returncode != 0:
            warn(f"pipeline.sh falhou pro video {video['id']} — pulando webhook")
            continue

        # Slug derivation: most recently touched memory/messages/<slug>/transcript.json.
        slug = ""
        if MESSAGES.exists():
            best = max(
                MESSAGES.iterdir(),
                key=lambda p: (
                    (p / "transcript.json").stat().st_mtime
                    if (p / "transcript.json").exists()
                    else 0
                ),
                default=None,
            )
            slug = best.name if best else ""
        if args.webhook and slug:
            _post_webhook(args.webhook, _build_webhook_payload(slug, video))

        processed.append(video["id"])

    if not args.dry_run:
        seen.update(processed)
        state["seen_video_ids"] = sorted(seen)
        state["last_run"] = datetime.utcnow().isoformat() + "Z"
        _save_state(state)

    print(
        json.dumps(
            {"ok": True, "processed": processed, "dry_run": args.dry_run},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
