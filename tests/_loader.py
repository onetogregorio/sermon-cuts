"""Helper: load a script that has a leading digit in its filename."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_script(filename: str) -> ModuleType:
    """``filename`` is the basename inside ``scripts/`` (e.g. ``06_build_srt.py``)."""
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    assert spec is not None and spec.loader is not None, f"could not load {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
