---
id: T-3531
title: 'CI output hygiene: faulthandler dumps at 100s spray 260 lines on healthy runs;
  raise the threshold and surface SUITE-RESULT in the step summary'
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- .github/workflows/ci.yml
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
OWNER REQUEST (2026-08-31): CI test output is still very messy even on
near-green runs. MEASURED on run 33353658750 (ubuntu, 21 min, 2 failures):
of 1518 log lines, ~260 are faulthandler thread-stack dump lines from just
4 "Timeout (0:01:40)!" per-test dumps -- pytest-timeout's
faulthandler_timeout=100 fires its FULL all-threads dump for every test
slower than 100s, which now includes the frob_self_scan_heavy group that
T-3525 legitimately allows 1200s. The dumps are pure noise on healthy runs
and bury the two real failures.

FIX:
 1. Raise faulthandler_timeout in pyproject.toml from 100 to a value above
    the heavy group's healthy runtime but below its 1200s cap (e.g. 600),
    updating the T-0692/T-3250 comment blocks that explain the number.
    Genuine hangs still dump (600s < the 1200s group timeout and the 40m
    step budget), normal-but-slow tests no longer spray 60-line stacks.
 2. Surface the signal, bury the noise: extend the ci.yml step-summary
    step (T-3516 added WORKER-CRASH-REPORT surfacing) to also put the
    SUITE-RESULT / SUITE-RESULT-FAILED block into $GITHUB_STEP_SUMMARY on
    every platform, so the failing set is readable without scrolling the
    raw log.
 3. Confirm captured-log noise on failures is bounded: pytest's
    log-capture for a failing test should show WARNING+ only (set
    log_level accordingly in pyproject if DEBUG/INFO are currently
    captured -- measured only 10 such lines this run, so this is the
    smallest part; skip it if already configured).
MUST-STAY-QUIET: a healthy slow test (150s sleep fixture with a 300s
marker) produces zero faulthandler dump lines.
MUST-FIRE: a genuinely hung test past faulthandler_timeout still dumps.
ACCEPTANCE: the next green-ish ubuntu run's Test-step log drops below
~600 lines with the failing set readable in the step summary.
