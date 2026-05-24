"""Smoke test for 05_validate_cut.is_forbidden_ending."""

from __future__ import annotations

from _loader import load_script

vc_mod = load_script("05_validate_cut.py")


def test_forbidden_endings_from_config() -> None:
    """Words listed in config/render_defaults.yaml `forbid_endings` should
    fail validation (cut shouldn't end on these)."""
    for word in vc_mod.CFG["forbid_endings"]:
        assert vc_mod.is_forbidden_ending(word), (
            f"word in forbid_endings list reported as OK: {word!r}"
        )


def test_punctuation_is_stripped_before_lookup() -> None:
    """The forbidden-ending check should normalize away trailing punctuation
    so 'porque,' is treated like 'porque'."""
    for word in vc_mod.CFG["forbid_endings"]:
        assert vc_mod.is_forbidden_ending(f"{word},")
        assert vc_mod.is_forbidden_ending(f"{word}.")
        assert vc_mod.is_forbidden_ending(f" {word.upper()}!")


def test_substantive_endings_pass() -> None:
    """Real content words (verbs, nouns, demonstratives) should never be
    flagged as forbidden — only the listed function-word-style endings do."""
    for word in ["Deus", "vida", "amor", "salvação", "veio", "disse", "perdoou"]:
        assert not vc_mod.is_forbidden_ending(word), (
            f"substantive word incorrectly flagged: {word!r}"
        )
