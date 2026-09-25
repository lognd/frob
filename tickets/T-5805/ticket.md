---
id: T-5805
title: 'frob ci report <run>: per-job, per-platform failures, cross-platform diff,
  clusters'
state: in-progress
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-c099f096
branch: t-draft-c099f096
scope:
- src/frob/_cli_parsers/_ci.py
- tests/unit/cli/test_ci_report.py
- src/frob/app/app.py
- src/frob/app/ci_runner.py
- src/frob/ghio.py
- tests/test_ghio.py
- docs/modules/ci_report.md
- tests/fixtures/ci_report
- docs/modules/ghio.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ci.py
  reason: frob ci report CLI wrapper (CI-1)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/cli/test_ci_report.py
  reason: frob ci report CLI wrapper (CI-1)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/app/app.py
  reason: 'CI-1: frob ci report app-layer wiring (app.py runner mapping, new ci_runner.py)
    plus in-scope fix to ghio.view_run''s rejected --json jobs field (measured gh
    2.4.0 gap); _root.py/_cli_parsers/__init__.py deferred, held by sibling COORD-1
    lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/app/ci_runner.py
  reason: 'CI-1: frob ci report app-layer wiring (app.py runner mapping, new ci_runner.py)
    plus in-scope fix to ghio.view_run''s rejected --json jobs field (measured gh
    2.4.0 gap); _root.py/_cli_parsers/__init__.py deferred, held by sibling COORD-1
    lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/ghio.py
  reason: 'CI-1: frob ci report app-layer wiring (app.py runner mapping, new ci_runner.py)
    plus in-scope fix to ghio.view_run''s rejected --json jobs field (measured gh
    2.4.0 gap); _root.py/_cli_parsers/__init__.py deferred, held by sibling COORD-1
    lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/test_ghio.py
  reason: 'CI-1: frob ci report app-layer wiring (app.py runner mapping, new ci_runner.py)
    plus in-scope fix to ghio.view_run''s rejected --json jobs field (measured gh
    2.4.0 gap); _root.py/_cli_parsers/__init__.py deferred, held by sibling COORD-1
    lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/ci_report.md
  reason: 'CI-1: frob ci report app-layer wiring (app.py runner mapping, new ci_runner.py)
    plus in-scope fix to ghio.view_run''s rejected --json jobs field (measured gh
    2.4.0 gap); _root.py/_cli_parsers/__init__.py deferred, held by sibling COORD-1
    lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/ci_report
  reason: 'CI-1: frob ci report app-layer wiring (app.py runner mapping, new ci_runner.py)
    plus in-scope fix to ghio.view_run''s rejected --json jobs field (measured gh
    2.4.0 gap); _root.py/_cli_parsers/__init__.py deferred, held by sibling COORD-1
    lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/ghio.md
  reason: view_run doc target for the --json jobs fix
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob ci report <run-id>: the T-2982 command surface over frob.ghio and frob.ci_report (T-5477 made the parser recognise this repo's SUITE-RESULT output): per job, per platform, the failing test node ids and failing steps, the cross-platform diff (shared vs platform-only), and a cluster grouping by file. Parity control: the CLI output equals build_run_report's own return for a fixture log with a known cluster. Errors are typed GhError values, never tracebacks (the T-2982 body's recorded '--log-failed returned EMPTY' mode gets a named error).
