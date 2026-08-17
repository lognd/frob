---
id: T-2252
title: frob quality check/test lack the granularity T-2244's Makefile leaf needs (ruff-format
  bundling, no dir-scoped test selection, no autofix write mode)
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/_python.py
- src/frob/app/test_runner.py
- src/frob/gates/_fix_engine*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2244 (repoint trivial Makefile aliases at frob quality/fmt) premise-checked
and found broken for 4 of its 9 target lines. Investigated directly against
this worktree's frob build, not assumed from --help text alone.

1. `frob fmt` is NOT a ruff-format equivalent. Its `run()`
   (src/frob/app/fmt_runner.py) canonicalizes `frob:` directive comment
   lines only (T-0441) -- it has nothing to do with `ruff check --fix`/
   `ruff format`, which is what Makefile's `format:` target actually does
   today. There is no frob subcommand today that performs a general
   ruff-autofix-and-format write pass.

2. `frob quality check`'s ruff stage bundles ruff-check and ruff-format
   under ONE `--skip-ruff` flag (src/frob/check/_python.py `_run_ruff`,
   two ToolResults from one call, no way to keep check and drop format
   independently). This repo's tree currently has ~120 files that would
   be reformatted by `ruff format --check` (verified directly, both via
   `frob quality check` and a raw `uv run ruff format --check src/
   tests/` -- 120 files, not a bare-vs-pinned-ruff artifact) -- i.e.
   `lint:`'s current definition (`ruff check` only, no format check) is
   deliberately narrower than what `frob quality check`'s bundled ruff
   stage would report. Repointing `lint:`/`typecheck:` through
   `frob quality check` as this ticket describes would make a currently-
   passing target start failing on ~120 pre-existing, out-of-scope
   formatting diffs -- not a mapping, a behavior change.

3. `_run_ruff` additionally shells bare `["ruff", ...]`, not
   `uv run ruff` -- playbook section 12's documented pinned-vs-PATH ruff
   drift hazard applies to this mapping specifically, a second
   independent parity risk on top of (2).

4. `frob quality check --fix` (src/frob/gates/_fix_engine*.py) only
   applies frob's own narrow, targeted Tier-A deterministic fixers
   (frob: directive suppress-comment repair, targeted E501 line
   shortening) -- never a general `ruff check --fix` across all
   fixable rule categories. It is not an equivalent to `lint-fix:`'s
   `ruff check --fix` + `ruff format`.

5. `frob quality test`'s `path` positional (cfg.test_path) is used
   ONLY to resolve the repo root to start from
   (src/frob/app/test_runner.py `_resolve_test_root`) -- it does not
   scope test SELECTION to that subdirectory. `--all` sets every
   runner's selection to the whole-suite sentinel regardless of `path`.
   There is no way today to reproduce `pytest tests/unit/ -q -n auto`'s
   subset semantics (or tests/integration, tests/system) via
   `frob quality test` -- only `--lang` (by language) and the touched-
   set diff selection exist, neither of which is directory-based.

What DID cleanly migrate and was verified with matching parity: `test:`
-> `uv run frob quality test --all` (python's `all_command` is `uv run
pytest -q`; `-n auto --dist=loadgroup --timeout=120` etc. already come
from pyproject.toml's own `[tool.pytest.ini_options] addopts`, so the
net pytest invocation is identical to today's `pytest tests/ -q -n
auto`). That migration alone does not satisfy T-2244's acceptance
criteria 1 (format:/lint:/lint-fix:/typecheck:) or the rest of
criteria 2 (test-unit:/test-integration:/test-system:), so T-2244
itself is failed rather than closed against unmet, evidence-bound
acceptance items.

Needed before a re-attempt at this leaf's remaining scope (real
src/frob work, deliberately out of a Makefile-only leaf):
- Split `frob quality check`'s ruff stage so ruff-check and ruff-format
  can be independently skipped, and switch `_run_ruff` to invoke
  `uv run ruff` (pinned) rather than bare `ruff`.
- Add a real ruff-autofix-and-format WRITE mode (not the narrow Tier-A
  fixers) so `format:`/`lint-fix:` have something to repoint to.
- Add directory/path-based test SELECTION scoping to `frob quality
  test` (not just root resolution) so `test-unit:`/`test-integration:`/
  `test-system:` have something to repoint to.

Filed as a residue ticket for whoever re-plans this leaf's remaining
scope with src/frob/** in bounds.
