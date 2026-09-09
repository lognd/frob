---
id: T-4354
title: uv run --project on tool-less target fails to resolve ruff/ty, faking a hard
  FAIL
state: in-progress
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
- src/frob/process/_project_tool.py
- tests/unit/test_project_tool.py
- docs/modules/process.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_project_tool.py
  reason: add coverage for the new tool-absent classifier this ticket introduces
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/process.md
  reason: new public symbol's frob:doc target
  actor: logan
  at: '2026-09-08'
evidence:
- tests/unit/test_project_tool.py::TestToolAbsent::test_true_on_spawn_failure
- tests/unit/test_project_tool.py::TestToolAbsent::test_false_unrelated_exit
- tests/unit/test_project_tool.py::TestToolAbsent::test_false_wrong_tool
- tests/unit/test_project_tool.py::TestResolveProjectTool::test_absent_err
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4352.

MEASURED root cause of the "ty exits 2 with no diagnostics" macOS failure
attributed to T-4352 (14 test failures): it is NOT actually caused by
src/frob/process/parsers/ty.py. All 14 failures assert r.returncode == 0 and
the tool-summary shows exactly ONE error line, always:

  [ruff-check] ruff produced no output -- the tool did not run (check its
  exit code/stderr), not a malformed report

`ty`'s own "process exited 2 with no diagnostics reported" line sits in the
SAME report's "Unmeasured gates" section (T-4309's routing works correctly)
and contributes zero to total_errors/total_warnings -- it never drives the
[FAIL] header or the nonzero returncode. Confirmed by grep across the full
macOS log: every one of the 14 "ty: process exited 2" occurrences has the
identical ruff-check hard error immediately above it, and that ERROR alone
accounts for `1 error` in every failing header.

ROOT CAUSE (reproduced locally, host-independent): project_tool_argv
(src/frob/process/_project_tool.py) builds `uv run --no-sync --project
<target> <tool> ...`. This resolves <tool> from the TARGET project's own
uv-managed environment/lockfile. Frob's test fixtures (tests/fixtures/
simple_python, and the ad-hoc projects _make_project writes into tmp_path)
do not declare ruff or ty as dependencies of their own pyproject.toml. When
the ambient PATH has no global ruff/ty binary for uv run to fall back to,
this fails with (reproduced locally by clearing PATH):

  error: Failed to spawn: `ty`
    Caused by: No such file or directory (os error 2)

exit code 2, and this text matches neither a ty diagnostic pattern (falls
through to T-4309's silent-nonzero-exit UNMEASURED path) nor is it caught
the way tool_no_output_result (T-4308, src/frob/process/parsers/common.py)
already catches the identical shape for ruff-check -- reporting a hard
ERROR diagnostic ("ruff produced no output"), which is what actually fails
these 14 tests.

Whether the runner has a global ruff/ty on PATH determines whether this
reproduces -- the same toolchain-cache-hit/miss shape T-4327 found twice
already. Present on macOS CI, apparently absent (or differently resolved)
on linux CI; unverified whether linux is genuinely unaffected or resolving
a stray global ruff/ty that happens to be compatible by luck, since this
session cannot reach macOS or reproduce the CI PATH exactly.

SUGGESTED FIX DIRECTIONS (not decided here, out of scope for this filing):
- Declare ruff/ty as dev-dependencies of the test fixture projects so
  uv run --project <target> resolves them from that project's own
  environment, as project_tool_argv's own docstring assumes every caller
  can rely on.
- Or give project_tool_argv an explicit, named fallback/failure mode for a
  target project that does not declare the tool at all, so behavior does
  not depend on what happens to be on the invoking host's PATH.
- Either way, ty's parser and ruff-check's parser should treat this
  identical "uv run could not spawn the tool inside the target env" shape
  the SAME way (currently one is a hard ERROR via tool_no_output_result,
  the other falls through to UNMEASURED) -- worth reconciling once the
  real fix lands so the reporting is consistent, not just the exit code.