"""Pytest config — make the project's ``scripts/`` importable as top-level
modules so individual scripts can be exercised in isolation.

Each pipeline script lives at ``scripts/NN_name.py`` with a leading digit,
so ``import 02_transcribe`` is not legal Python. We sidestep that by
loading them via ``importlib.util.spec_from_file_location`` in each test.
``conftest.py`` only needs to put ``scripts/`` on sys.path so ``_common``
imports work when the scripts are exec'd."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "scripts"
# Make ``_common`` importable when scripts are loaded via _loader.load_script,
# AND make ``_loader`` itself importable from sibling test files (when tests/
# is a package, pytest doesn't add it to sys.path automatically).
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))
