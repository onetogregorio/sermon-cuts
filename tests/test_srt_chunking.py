"""Smoke test for 06_build_srt's chunking rules.

The brand subtitle look depends on these breaks staying stable across
refactors — a regression here is visible in every cut, so we lock down
a small set of properties on a real sample transcript.
"""

from __future__ import annotations

import json

from _loader import ROOT, load_script

build_srt_mod = load_script("06_build_srt.py")
SAMPLE = ROOT / "examples" / "vinde_transcript_sample.json"


def _entries(start: float, end: float, hook_boost: bool = False) -> list:
    data = json.loads(SAMPLE.read_text())
    return build_srt_mod.build_srt(data["words"], start, end, hook_boost=hook_boost)


def test_returns_some_cues_on_a_30s_window() -> None:
    entries = _entries(0.0, 30.0)
    assert len(entries) > 3, "30s of speech should yield more than 3 cues"


def test_cue_chars_respect_max() -> None:
    entries = _entries(0.0, 30.0)
    for _start, _end, text in entries:
        # Strip the optional ASS override the hook_boost adds, then check
        # the visible text against the configured max_chars (with a small
        # slack for soft-break sites where we let the cue close slightly
        # over rather than orphan a function word).
        visible = text.lstrip("{")
        if "}" in visible:
            visible = visible.split("}", 1)[1]
        assert len(visible) <= build_srt_mod.MAX_CHARS + 6, (
            f"cue too long ({len(visible)} chars): {visible!r}"
        )


def test_majority_of_cues_avoid_forbidden_endings() -> None:
    """Most cues shouldn't end on a 'porque'/'mas'/'que' style word — those
    reads visually as the cue being cut mid-thought. We don't enforce ZERO
    because in tight chunks the function-word shifter has to choose between
    a trailing 'de' and an overflow on the next cue, and overflow loses.

    This test catches a regression where the shifter stops working entirely:
    if more than ~20% of cues end on a forbidden ending we'd notice."""
    import yaml

    forbid = set(
        yaml.safe_load((build_srt_mod.SKILL_ROOT / "config/render_defaults.yaml").read_text())[
            "cut_validation"
        ]["forbid_endings"]
    )
    entries = _entries(0.0, 60.0)
    bad = 0
    total = max(1, len(entries) - 1)  # last entry is exempt
    for _start, _end, text in entries[:-1]:
        words = text.rstrip(".,!?;:").split()
        if not words:
            continue
        last = words[-1].strip(".,!?;:").lower()
        if last in forbid:
            bad += 1
    ratio = bad / total
    assert ratio < 0.20, (
        f"too many cues ({bad}/{total} = {ratio:.1%}) end on a forbidden word — shifter regressed?"
    )


def test_hook_boost_prefixes_first_cue_only() -> None:
    boosted = _entries(0.0, 30.0, hook_boost=True)
    plain = _entries(0.0, 30.0, hook_boost=False)
    assert boosted[0][2].startswith(build_srt_mod.HOOK_PREFIX), (
        "first cue should start with the hook ASS override when hook_boost=True"
    )
    # All cues after the first must NOT carry the prefix.
    for entry in boosted[1:]:
        assert not entry[2].startswith(build_srt_mod.HOOK_PREFIX)
    # Disabling hook_boost yields no prefix on any cue.
    for entry in plain:
        assert not entry[2].startswith(build_srt_mod.HOOK_PREFIX)
