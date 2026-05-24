#!/usr/bin/env python3
"""Validate a proposed cut's start/end land on natural boundaries.

If the cut ends mid-thought (last word is in `forbid_endings` like "porque",
"mas", "que", "para"), tries to EXTEND the end to the next valid VAD
candidate cut point.

If the cut starts mid-sentence, tries to BACK UP the start to the previous
candidate.

Usage:
    05_validate_cut.py <slug> <cut_index>
                       [--max-extend-s 8] [--write-back]

Reads:
    memory/messages/<slug>/transcript.json
    memory/messages/<slug>/vad.json
    memory/messages/<slug>/cuts_proposed.json
Output:
    JSON: {ok, original_start, original_end, adjusted_start, adjusted_end,
           reason, last_word, ending_punct}
If --write-back: updates cuts_proposed.json in place.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())["cut_validation"]


def find_last_word(words: list[dict], t_end: float) -> dict | None:
    last = None
    for w in words:
        if w.get("type") != "word" or w.get("start") is None:
            continue
        if w["start"] >= t_end:
            break
        last = w
    return last


def find_first_word_after(words: list[dict], t: float) -> dict | None:
    for w in words:
        if w.get("type") == "word" and w.get("start") is not None and w["start"] >= t:
            return w
    return None


def is_forbidden_ending(text: str) -> bool:
    norm = text.strip(",.;:!? ").lower()
    return norm in CFG["forbid_endings"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int, help="1-based index in cuts_proposed.json")
    ap.add_argument("--max-extend-s", type=float, default=8.0)
    ap.add_argument("--write-back", action="store_true")
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    transcript = json.loads((msg_dir / "transcript.json").read_text())
    vad = json.loads((msg_dir / "vad.json").read_text())
    cuts = json.loads((msg_dir / "cuts_proposed.json").read_text())
    candidates = sorted(vad["candidate_cut_points"])

    if args.cut_index < 1 or args.cut_index > len(cuts):
        sys.exit(f"cut_index {args.cut_index} out of range (1..{len(cuts)})")
    cut = cuts[args.cut_index - 1]
    orig_start, orig_end = float(cut["start"]), float(cut["end"])

    words = transcript["words"]
    last = find_last_word(words, orig_end)
    last_text = (last.get("text") or "") if last else ""

    adj_end = orig_end
    reason = "ok"
    if last and is_forbidden_ending(last_text):
        # Extend forward until ending word is NOT forbidden AND aligns to VAD candidate
        for c in candidates:
            if c <= orig_end:
                continue
            if c - orig_end > args.max_extend_s:
                reason = f"could not extend within {args.max_extend_s}s; last word still '{last_text}'"
                break
            new_last = find_last_word(words, c)
            if new_last and not is_forbidden_ending(new_last.get("text") or ""):
                adj_end = c
                reason = f"extended +{c - orig_end:.2f}s to land after '{(new_last.get('text') or '').strip()}'"
                last = new_last
                last_text = new_last["text"]
                break

    adj_start = orig_start
    # Start is NEVER auto-modified: it represents the curator's (LLM or human)
    # deliberate intent about where the cut should begin. We only report the
    # nearest prior VAD candidate as advisory info — moving it would override
    # a hand-picked in-point. Bug reproduced when LLM picked start=97.92 to
    # land exactly on "às vezes" and validate snapped it back to 95.252 (the
    # previous VAD candidate, mid-sentence), ruining the hook.
    nearest_prior_candidate = None
    prev_cands = [c for c in candidates if c <= orig_start and orig_start - c <= 3.0]
    if prev_cands:
        nearest_prior_candidate = max(prev_cands)

    last_text_clean = (last_text or "").strip()
    ending_punct = last_text_clean[-1] if last_text_clean and last_text_clean[-1] in ".!?,;:" else ""

    result = {
        "ok": not is_forbidden_ending(last_text),
        "cut_index": args.cut_index,
        "original_start": orig_start,
        "original_end": orig_end,
        "adjusted_start": adj_start,
        "adjusted_end": adj_end,
        "nearest_prior_vad_candidate": nearest_prior_candidate,
        "last_word": last_text_clean,
        "ending_punctuation": ending_punct,
        "reason": reason,
    }

    if args.write_back and (adj_start != orig_start or adj_end != orig_end):
        cut["start"] = adj_start
        cut["end"] = adj_end
        cut["duration_s"] = round(adj_end - adj_start, 2)
        cut["ending_word"] = last_text_clean
        cut["ending_punctuation"] = ending_punct
        (msg_dir / "cuts_proposed.json").write_text(
            json.dumps(cuts, indent=2, ensure_ascii=False))
        result["written_back"] = True

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
