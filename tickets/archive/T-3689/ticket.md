---
id: T-3689
title: win32 check slow/hangs after T-3686 self-interrupt fix
state: done
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/process/**
- tests/conftest.py
- .github/workflows/ci.yml
- tests/unit/test_check_admission.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-3689 Done report
  actor: logan
  at: '2026-09-02'
  old_length: 82
  new_length: 93
- mode: append
  reason: condense timing-mark process-start rationale into T-3689 body
  actor: logan
  at: '2026-09-19'
  old_length: 317
  new_length: 1232
- mode: append
  reason: condense timing-breadcrumb env-knob rationale into T-3689 body
  actor: logan
  at: '2026-09-19'
  old_length: 1232
  new_length: 3137
evidence:
- tests/unit/test_check_admission.py::TestTimingDebug::test_disabled_by_default
- tests/unit/test_check_admission.py::TestTimingDebug::test_enabled_when_set_non_empty
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_is_silent_when_disabled
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_prints_breadcrumb_when_enabled
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_elapsed_grows_with_process_start_offset
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3686. See conversation for detail. References T-3686 T-3683 T-3256.

test line

## Restore log
- 2026-09-02: T-3689 self-gate: amend Done report to cite T-3708, the follow-up that resolved the deferred pool-teardown investigation this ticket's Done report disclosed without a citing ticket id (TICK011)

<!-- narrative-moved:src/frob/check/__init__.py:133:T-3689 -->
: T-3689: process-start reference `_timing_mark` measures elapsed time
: against -- captured once, at import time, which for a `frob check`
: CLI invocation (a fresh, single-shot `python`/`uv run` process) is
: indistinguishable in practice from "process start" (the gap is
: import-resolution time for `frob.check` itself and its transitive
: imports, microseconds to low milliseconds, not seconds) -- exactly
: the same "one-shot process, import time ~= process start" premise
: `frob.check._memo`'s own per-run counters already rely on. A
: per-call `time.monotonic()` capture at `_run_check_with_skips`'s own
: first line would be marginally more precise but would need
: threading a `start` value through every `_stop_before_result` call
: site for a precision gain this diagnostic (localizing tens of
: seconds, not milliseconds) does not need.

<!-- narrative-moved:src/frob/check/__init__.py:102:T-3689 -->
: T-3689: env-gated timing-breadcrumb knob, OFF by default everywhere,
: sibling to `FROB_CHECK_STOP_BEFORE_ENV` -- where that knob EXITS the
: pipeline at a named point, this one keeps running but PRINTS an
: elapsed-seconds-since-process-start breadcrumb at every one of the
: same `_CHECK_STOP_POINTS` (via `_stop_before_result`'s own call
: sites, unconditionally reached regardless of whether the point
: matches `FROB_CHECK_STOP_BEFORE`) plus 3 extra sub-phase points
: inside `_early_precheck_failure` (T-3256/T-2764/T-3526's own 3
: prechecks) that the 7 pipeline-wide stop points cannot see inside
: of. Exists because T-3686 fixed the win32 self-interrupt (pid_alive
: no longer broadcasts CTRL_C_EVENT) and UNMASKED a second win32
: problem the stop-before knob cannot localize on its own: `frob
: check` now runs to completion on win32 but a zero-tool-spawn diag
: (FROB_DISABLE_EXEC=1) took 122.7s instead of the expected low
: single digits (CI run 33615554440). `FROB_CHECK_STOP_BEFORE` only
: proves a bracket is clean or dirty by EXITING there -- it cannot
: say how long a run that completes anyway took to cross each point.
: This flag turns the same 7 points (plus the 3 precheck sub-phases)
: into elapsed-time breadcrumbs instead, so the NEXT windows CI run's
: `FROB-CHECK-TIMING:` lines localize where the 122s actually goes
: without needing a new bisect round per candidate point.
:
: T-3689: PRIVATE (leading underscore), unlike its public `FROB_CHECK_
: STOP_BEFORE_ENV` sibling -- `docs/commands/check.md` (the natural
: `frob:doc` home for a public sibling knob) sits outside this
: ticket's own declared scope, so this stays undocumented-but-private
: rather than public-but-undocumented; documenting it there (and
: making it public) is deferred to a follow-up ticket that touches
: `docs/commands/check.md`.