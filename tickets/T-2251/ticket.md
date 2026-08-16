---
id: T-2251
title: 'frob format subcommand: replace make format/lint-fix/all (ruff fix+format
  wrapper)'
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/app.py
- src/frob/app/pyfmt_runner.py
- src/frob/_cli_parsers/**
- tests/unit/test_pyfmt_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Split from T-1382 (measured 2026-08-10, see T-1382's own body for the full
21-target classification table).

Four Makefile targets have NO frob subcommand equivalent today and are
genuine (b) gaps:

- `all` (core + `ruff check --fix --select I` + `ruff format` + `ty check`)
- `format` (`ruff check --fix --select I` + `ruff format`)
- `lint-fix` (`ruff check --fix` [all rules] + `ruff format`) -- superset of
  `format`'s fix scope
- `upload` (bump_version.py + `frob release stamp` + publish) -- highest
  risk, lowest frequency; do last

`lint`/`typecheck`/`test`* /`core`/`check`/`clean`/`coverage-fast`/
`deploy-audit`/`pool-*` are ALREADY thin wrappers over an existing frob
subcommand (`frob check --only lint`, `frob check --only ty`, `frob test
[path] [--all]`, `frob natives build`, `frob check`, `frob clean --all -y`,
`frob coverage .`, `frob deploy audit`, `frob scaffold pool ...`) -- no
work needed there. `coverage` (the heavy crash-recovery recipe) is a
DELIBERATE T-1516/T-1526 decision to keep the shell logic Makefile-side,
not a gap. `install`/`install-tool` are bootstrap targets (uv sync / uv
tool install) that cannot become a frob subcommand without a chicken-and-
egg problem. `playbook` (`cat docs/...`) and `sync-skills` (syncs
agents/skills, which CLAUDE.md flags for removal/rework) are both out of
this ticket's scope -- `sync-skills` in particular should be revisited
alongside whatever ticket removes/reworks `agents/`/`skills/`, not here.

Blocked on scope: implementing `format`/`lint-fix`/`all` requires wiring a
new `Subcommand` member into `src/frob/app/app.py`'s closed
`_SUBCOMMAND_RUNNER_NAMES` dict and `_import_runner_module`'s if/elif
chain (T-1337's OPAQUE001 fail-closed pattern) -- `app.py` was NOT granted
by T-1382's implicit CLI-wiring scope (only `__main__.py`, `app/config.py`,
`app/ticket_runner/__init__.py` are), so this needed its own ticket with
`src/frob/app/app.py` explicitly in scope rather than widening T-1382 back
out after it was narrowed for TICK009.

Suggested design: one new runner module (`src/frob/app/pyfmt_runner.py`)
wrapping `ruff check --fix [--select I]` + `ruff format` as two subprocess
calls (mirror `src/frob/check/_python.py::_run_ruff`'s tool-missing/
kill-switch handling, but write instead of `--check`), exposed as a new
top-level `frob format [--select-imports-only]` subcommand (name chosen to
avoid colliding with the existing `frob fmt`, which does directive-comment
canonicalization, a different concern). `lint-fix` becomes `frob format`
with no `--select-imports-only` flag; `format` becomes `frob format
--select-imports-only`; `all` becomes `frob natives build && frob format
--select-imports-only && frob check --only ty`.
