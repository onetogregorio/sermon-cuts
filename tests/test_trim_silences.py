"""Smoke test for 09_trim_silences.compute_keep_intervals."""

from __future__ import annotations

from _loader import load_script

trim_mod = load_script("09_trim_silences.py")


def test_no_silences_returns_whole_window() -> None:
    intervals = trim_mod.compute_keep_intervals(
        silences=[], cut_start=10.0, cut_end=70.0, threshold_s=2.5, keep_silence_s=1.0
    )
    assert intervals == [(0.0, 60.0)]


def test_short_silence_below_threshold_is_kept_intact() -> None:
    """A pause shorter than threshold_s isn't worth compressing — the
    interval list should still treat the cut as one continuous block."""
    intervals = trim_mod.compute_keep_intervals(
        silences=[{"start": 30.0, "end": 31.5}],  # 1.5s pause, threshold 2.5s
        cut_start=0.0,
        cut_end=60.0,
        threshold_s=2.5,
        keep_silence_s=1.0,
    )
    assert intervals == [(0.0, 60.0)]


def test_long_silence_collapses_to_keep_silence() -> None:
    """A 5s silence at t=10 should keep 1s (0→11) and skip the rest (15→end)."""
    intervals = trim_mod.compute_keep_intervals(
        silences=[{"start": 10.0, "end": 15.0}],
        cut_start=0.0,
        cut_end=30.0,
        threshold_s=2.5,
        keep_silence_s=1.0,
    )
    assert intervals == [(0.0, 11.0), (15.0, 30.0)]


def test_silence_outside_cut_window_is_ignored() -> None:
    """Pauses in the source video that fall outside [cut_start, cut_end]
    must not affect the cut's intervals — they belong to other cuts."""
    intervals = trim_mod.compute_keep_intervals(
        silences=[{"start": 200.0, "end": 210.0}],
        cut_start=10.0,
        cut_end=70.0,
        threshold_s=2.5,
        keep_silence_s=1.0,
    )
    assert intervals == [(0.0, 60.0)]


def test_saves_match_arithmetic() -> None:
    """Sanity: the sum of keep-intervals should equal cut_dur - savings."""
    intervals = trim_mod.compute_keep_intervals(
        silences=[
            {"start": 100.0, "end": 105.0},  # 5s long, threshold 2.5s → save 4s
            {"start": 130.0, "end": 130.5},  # below threshold → no save
        ],
        cut_start=95.0,
        cut_end=145.0,  # 50s window
        threshold_s=2.5,
        keep_silence_s=1.0,
    )
    total_kept = sum(b - a for a, b in intervals)
    assert abs(total_kept - 46.0) < 0.01, f"expected ~46s kept, got {total_kept}"
