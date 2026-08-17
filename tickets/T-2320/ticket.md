---
id: T-2320
title: 'frob quality check: split ruff-check/ruff-format skip flags + add a real ruff-autofix/format
  write mode'
state: queued
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/_python.py
- src/frob/check/__init__.py
- src/frob/gates/_fix_engine*.py
- src/frob/_cli_parsers/_check.py
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-2252. `_run_ruff` (src/frob/check/_python.py) bundles
ruff-check and ruff-format under one `--skip-ruff` flag with no way to
skip them independently, and `frob quality check --fix`
(src/frob/gates/_fix_engine*.py) only applies frob's own narrow,
targeted Tier-A deterministic fixers -- never a general `ruff check --fix`
across all fixable rule categories. Neither is an equivalent to
Makefile's `format:`/`lint-fix:` targets (`ruff check --fix` + `ruff
format`).

Needed before T-2244's `format:`/`lint:`/`lint-fix:`/`typecheck:` Makefile
leaves can repoint cleanly:
- Split the ruff stage's skip flag into independent
  `--skip-ruff-check`/`--skip-ruff-format` (currently one bundled
  `--skip-ruff`).
- Add a real ruff-autofix-and-format WRITE mode (a genuine `ruff check
  --fix` + `ruff format` pass, distinct from the existing narrow Tier-A
  fixers) so `format:`/`lint-fix:` have something to repoint to.

Also note: this repo's tree currently has ~120 files that would be
reformatted by `ruff format --check` (verified directly) -- repointing
`lint:`/`typecheck:` through `frob quality check`'s bundled ruff stage as
originally proposed would turn a currently-passing Makefile target into a
failing one on pre-existing, out-of-scope formatting diffs. Whoever picks
this up should either accept that one-time reformat as part of the
migration or keep `lint:` scoped to ruff-check only via the new split
flag.
