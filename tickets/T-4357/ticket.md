---
id: T-4357
title: Windows-only false refuse in pre-land ruff diff-attribution (non-reproducible)
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land_lint_diff_attribution.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4351 (Windows completes with 4 platform-specific
failures).

MEASURED, single occurrence in the FIRST completed Windows suite run of
this drive (SUITE-RESULT: exitstatus=1 collected=13786 failed=5):

  tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse

  tests\test_ticket_land_lint_diff_attribution.py:167: in test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
      _assert_touched_files_lint_clean_pre_land(
  src\frob\app\ticket_runner\_land_cmd.py:4814: in _assert_touched_files_lint_clean_pre_land
      _refuse_pre_land_lint(ticket_id, new_violations, py_files)
  src\frob\app\ticket_runner\_land_cmd.py:4844: in _refuse_pre_land_lint
      sys.exit(1)
  E   SystemExit: 1

This test's own fixture (repo) commits a .py file with a pre-existing
F401 violation and NO pyproject.toml at the repo root, then merely
shifts that violation's line and asserts the land is NOT refused
(T-3132: identity is (relative_file, code, message), blind to
line/col). Landing this asserted a genuinely-new violation instead,
which only happens via _assert_touched_files_lint_clean_pre_land's
"baseline unmeasurable" degrade path (baseline_counts is None ->
new_violations = ALL current diagnostics, including the pre-existing
one).

STRONG SUSPECT, not confirmed: this function's own T-4257 fix already
documents an adjacent Windows-only fragility in the SAME code path --
project_tool_argv's uv run --no-sync --project <root> ruff ... falls
back to bare-PATH resolution when root carries no pyproject.toml
(exactly this fixture's shape), which T-4257 found "MEASURABLY fails on
Windows" for the CURRENT-pass spawn and fixed with a sys.executable -m
ruff fallback when stdout comes back empty. The BASELINE pass
(_ruff_baseline_diagnostic_identities -> _ruff_check_files(snapshot,
..., resolve_root=worktree)) runs through the exact same function and
fallback, so on the surface both passes should degrade identically --
but the two spawns run in DIFFERENT directories (worktree vs the
baseline snapshot's detached git worktree under system TEMP) and
possibly under a DIFFERENT ambient VIRTUAL_ENV-fallback outcome per
T-4308/uv's "prefer an already-active compatible VIRTUAL_ENV" behavior,
so an asymmetric spawn result (one pass gets real ruff output via an
active-venv fallback that happens to resolve, the other spawn hits the
Windows-only PATH-resolution failure this same T-4257 already named,
depending on process-scheduling/AV-scan timing) would produce exactly
this "baseline unmeasurable -> everything treated as new" symptom.

NOT CONFIRMED: could not reproduce on the available Windows mirror
despite substantial effort -- single run (isolated node id), 15x serial
loop, 10x serial loop via uv run pytest (matching CI's own launch
shape), whole test module together (6 items) with and without xdist,
.venv\Scripts\python.exe -m pytest directly (no ambient VIRTUAL_ENV,
forces the T-4257 fallback path every time) and via uv run pytest
(ambient VIRTUAL_ENV active, matching CI's Windows step's own
Start-Process -FilePath uv -ArgumentList run,pytest,... launch). All of
the above passed every time on this mirror. This may be a rare, load-
or scheduling-dependent flake specific to the full 13786-test Windows
CI run (heavy concurrent git worktree add/ruff spawns, possible AV-scan
interference on freshly created files) rather than a deterministic bug
-- the next COMPLETE Windows suite run is the cheapest way to learn
whether this recurs before spending more investigation budget on it.

Do not close as fixed without a second MEASURED Windows failure (or a
confirmed repro) to verify against.