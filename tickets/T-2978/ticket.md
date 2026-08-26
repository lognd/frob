---
id: T-2978
title: 'Long-running commands show no live progress: no phase, no unit count, no elapsed
  time on a TTY'
state: done
kind: ux
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
- src/frob/app/check_runner.py
- src/frob/render/_renderer.py
- docs/modules/render.md
- docs/modules/check.md
- tests/unit/test_check.py
- tests/unit/test_app_runners_batch6.py
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/check_runner.py
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/render/_renderer.py
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/render.md
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/check.md
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_check.py
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/system/test_cli_check.py
  reason: live per-task progress for frob check (TTY-only, reuses existing T-0419
    Progress primitive; per-gate/branch-scan progress for other commands filed as
    follow-up)
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/test_check.py::TestCollectResultsProgressCallback::test_on_task_done_fires_once_per_task_with_final_total
- tests/unit/test_check.py::TestCollectResultsProgressCallback::test_results_stay_in_submission_order_regardless_of_callback
- tests/unit/test_check.py::TestCollectResultsProgressCallback::test_no_callback_matches_pre_t2978_behavior_exactly
- tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_none_progress_returns_none
- tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_updates_progress_with_language_qualified_label
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 81b56fcd56e71c8dc4388cf809d432ff05869208
---
Long-running frob commands give the interactive operator nothing to look at
while they run. Measured this session:

- `frob check` full run: 274s, and a rapid land's inline check measured
  241.59s at 115% CPU before T-2913 removed it.
- `frob status` was 5m41s before T-2950 (now 0.554s).
- `frob verify now`, `frob sys audit`, `frob dup`, the branch-classification
  scan (~5m48s over 1092 branches) are all multi-minute.
- `frob ticket doable` measured 92-99s.

During all of that the terminal shows either nothing or unstructured debug
lines, so the operator cannot tell the difference between "working", "stuck",
and "about to time out". That matters more than cosmetics here: this session
repeatedly had to reach for `ps --ppid`, `PYTHONFAULTHANDLER`, and log
greps just to answer "is this progressing?" -- and a land at 7% CPU was twice
misread as stalled when a child process was doing the work.

WHAT IS WANTED: a live progress surface for interactive (TTY) runs -- units
completed against a denominator where one exists (files parsed / N tracked,
gates run / N gate families, branches scanned / N), the current phase or gate
name, and elapsed time. Per-gate timings ALREADY exist (gate-summary prints
`archgate=28.17s, clones=8.82s, ...`), so the data is largely there; it is
reported only after the fact.

CONSTRAINTS
- TTY-only. Machine paths (`--json`, non-TTY, CI) must stay byte-identical --
  `frob.logging.color.should_color`'s existing TTY/NO_COLOR/FORCE_COLOR
  decision is the precedent to reuse, not a second mechanism.
- Must not slow the work it measures. Report the overhead you measure.
- A denominator that is not known must not be faked. "parsed 412 files" with
  no total is honest; "412/500" invented is not.
- Do not print a spinner that keeps animating when the underlying work has
  stopped -- a progress indicator that cannot distinguish progress from a hang
  is worse than none, and this repo has paid for that class of lie repeatedly.

ACCEPTANCE
- Given an interactive TTY run of a multi-minute command, when it runs, then
  the operator sees the current phase, a unit count (with a denominator where
  one genuinely exists), and elapsed time, updating as work proceeds.
- Given `--json` or a non-TTY stream, when the same command runs, then output
  is byte-identical to today. Prove with a diff.
- Given instrumentation enabled, when the command runs, then the measured
  overhead is reported and is a small fraction of total runtime.