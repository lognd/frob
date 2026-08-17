---
id: T-2319
title: 'frob quality test: path positional only resolves root, never scopes SELECTION
  to a subdirectory'
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
- src/frob/app/test_runner.py
- src/frob/_cli_parsers/_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-2252. `frob quality test`'s `path` positional
(`cfg.test_path`, src/frob/app/test_runner.py `_resolve_test_root`) is
used ONLY to resolve the repo root to start from -- it does not scope
test SELECTION to that subdirectory. `--all` sets every runner's
selection to the whole-suite sentinel regardless of `path`. There is no
way today to reproduce `pytest tests/unit/ -q -n auto`'s subset semantics
(or tests/integration, tests/system) via `frob quality test` -- only
`--lang` (by language) and the touched-set diff selection exist, neither
of which is directory-based.

Needed before T-2244's `test-unit:`/`test-integration:`/`test-system:`
Makefile leaves can repoint cleanly: add directory/path-based test
SELECTION scoping to `frob quality test` (not just root resolution), so
a caller can express "run only tests/unit/" (or integration/system)
through the frob CLI the same way a bare `pytest tests/unit/` does today.
