# Contributing to Sermon Cuts

Thanks for wanting to make this better. This project is small, opinionated,
and used in production by the maintainer (read: dogfooded weekly), so
contributions follow a deliberately tight loop.

## How it works

1. **Open an issue first** for anything non-trivial — features, behavior
   changes, new dependencies, anything touching the rendering pipeline
   or the brand-style defaults. Bug reports don't need a pre-issue but
   are welcome anyway.

2. **Fork → branch → PR.** Direct pushes to `main` are blocked for
   non-maintainers; PRs are the only path in.

3. **All PRs require maintainer review** before merge. This is enforced
   via [CODEOWNERS](.github/CODEOWNERS) and branch protection on `main`
   (see the maintainer setup section below).

4. **CI must pass.** The workflow at `.github/workflows/ci.yml` runs:
   - `ruff check` + `ruff format --check` on `scripts/`
   - `pytest tests/` — currently 12 snapshot tests
   - `yamllint` on `config/`
   - `gitleaks` secret scan over the full history
   - schema validation on `render_defaults.yaml` + `force_style.txt`

   Don't bypass these. If a check fails for an unrelated reason, mention
   it in the PR — don't disable it.

## What changes are welcome

- Bug fixes to scripts in `scripts/`
- Better heuristics in `06b_scrub_srt.py` (more proper nouns,
  better dropped-word detection, new patterns)
- New transcription providers in `02_transcribe.py`
  (follow the existing `transcribe_<name>()` shape)
- New subtitle style presets in `config/style_presets/`
- Doc clarifications in `docs/` and the READMEs (PT/EN/ES kept in sync)
- Bug fixes in the landing under `site/`

## What needs discussion first

- Changes to the brand-style defaults in `docs/STYLE.md`
- New top-level scripts (anything `NN_*.py`)
- New runtime dependencies in `requirements.txt`
- Anything that changes the pipeline's output shape

Open an issue and we'll talk it through before you spend time coding.

## Coding conventions

- Python: ruff-format clean, `from __future__ import annotations` at top,
  type hints on public functions.
- Standalone scripts — no circular dependency between them. Shared
  helpers live in `scripts/_common.py`.
- JSON output goes to **stdout** (machine-readable). Logs go to **stderr**
  (`print(..., file=sys.stderr)`).
- Commit messages in English, conventional-commit style:
  `feat(scope): …`, `fix(scope): …`, `docs(scope): …`, `chore(scope): …`.
- Comments can mix PT-BR and English — match the existing tone.

## Maintainer setup: branch protection

GitHub doesn't let you commit branch-protection rules from a repo file,
so this lives here as a checklist. Run once per repo:

1. Go to **Settings → Branches → Add branch protection rule**.
2. Branch name pattern: `main`
3. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require approvals — **1**
   - ✅ Dismiss stale approvals on new commits
   - ✅ Require review from Code Owners
   - ✅ Require status checks to pass before merging
     - Add `lint` and `secret-scan` jobs from the `ci` workflow
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings (incl. admins, if you
     want to enforce on yourself too)
4. Optional but recommended:
   - ✅ Restrict pushes that create matching branches → only allow PRs
   - ✅ Lock branch (read-only outside of PRs)
5. Save.

Verify with a quick test:
```bash
git checkout main
echo "test" >> README.md
git commit -am "test direct push" && git push origin main
# → should be rejected: "protected branch hook declined"
git reset --hard origin/main   # undo locally
```

## Reporting security issues

See [SECURITY.md](SECURITY.md). Don't open a public issue for
vulnerabilities — email `web@conversaoextrema.com.br`.
