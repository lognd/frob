---
id: T-3673
title: 'win32 round 17: elimination controls (e/f) + mitigation validation (a2) +
  suite guard'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
- tests/conftest.py
- src/frob/process/_guard.py
- docs/modules/process.md
- tests/unit/test_conftest_console_ctrl_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_console_ctrl_guard.py
  reason: unit tests for the FROB_TEST_IGNORE_CONSOLE_CTRL gating logic added to tests/conftest.py
  actor: logan
  at: '2026-09-01'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Round 16's four-variant matrix (T-3670) exonerated guarded tool
children, uv ancestry, and ProcessPoolExecutor preload -- all four
variants still received T-3648-SIGNAL at ~1.3-1.5s. The remaining
suspects are (i) the environment itself (pwsh Start-Process/conhost/
runner delivering a console ctrl event to every console-attached
child) or (ii) frob's own in-process startup (import-time side
effect).

Round 17 adds two elimination controls to the same diag step:

  (e) trivial-python control: same Start-Process harness and signal
      logger preamble as variant (a), but the child NEVER imports
      frob -- it just time.sleep(5) and exits 0. Dirty (e) exonerates
      frob entirely (environment is the sender) and unblocks
      mitigation. Clean (e) implicates frob's own startup and hands
      off to (f).

  (f) import-only control: child does `import frob` and nothing else,
      then sleep(5), exit 0. Clean (f) + dirty (a-d) points at the
      check pipeline pre-thread-start; dirty (f) points at import-time
      side effects (audit signal handler registrations at import).

MITIGATION VALIDATION in the same round, using the existing
FROB_WIN32_IGNORE_CONSOLE_CTRL scope landed in T-3657 (env-gated,
default-off, src/frob/process/_guard.py::win32_console_ctrl_ignore_scope,
already wrapping run_check in src/frob/check/__init__.py):

  (a2) baseline variant (a) but with FROB_WIN32_IGNORE_CONSOLE_CTRL=1
      set before invoking uv. Acceptance: NO T-3648-SIGNAL line, and
      the diag exits with a genuine gate result (0 or nonzero-not-130).

If (e) proves an environment sender AND (a2) validates the
mitigation, this ticket ALSO protects the SUITE (not just the diag):
add an env-gated (FROB_TEST_IGNORE_CONSOLE_CTRL=1) win32
console-ctrl-ignore in tests/conftest.py session setup, reusing the
same SetConsoleCtrlHandler approach as win32_console_ctrl_ignore_scope
(gating logic gets its own unit test), and set that env var ONLY in
the CI workflow's windows Test step -- implemented now but left
env-gated off in general use. Rationale, documented loudly in
docs/modules/process.md: the suite's teardown KeyboardInterrupt
(threading join at session teardown) is the same injected-signal
class killing the leg at ~100% completion after 3 consecutive runs;
non-interactive CI has no legitimate console Ctrl-C to respect, so
masking is justified there while the sender identity (environment vs
frob) stays tracked in this ticket family rather than being declared
closed.

Coordination: tests/conftest.py is currently unowned (T-3658 landed);
verified no live lease before citing it in scope (checked via
`frob lease list` at ticket-filing time).

References: T-3670 (round 16, filed the 4-variant matrix this round
extends), T-3657 (round 15, landed the mitigation scope this round
validates), T-3651 (round 14, falsified the tool-child hypothesis),
T-3648 (signal logger + diag scaffolding origin).

Scope: .github/workflows/ci.yml + tests/test_ci_workflow_matrix.py +
tests/conftest.py (suite guard, env-gated off) +
src/frob/process/_guard.py (only if variant (f) names an import-time
defect) + docs/modules/process.md.
