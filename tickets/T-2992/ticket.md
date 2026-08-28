---
id: T-2992
title: capture and triage the real test failures the ubuntu CI hang was hiding
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: pure investigation/triage record -- surface, enumerate,
  and file per-failure tickets once a clean unscoped run exists
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2980 fixed the CI hang caused by tests/system/conftest.py's run()
defaulting to an unbounded subprocess wait. With that fix in place the
suite now runs to termination on Linux instead of hanging, but doing so
surfaces real, pre-existing test failures that the hang was hiding
(this is separate from the earlier T-2943 macOS mis-attribution -- that
was a different investigation's mistake, this is simply "the hang
prevented us from ever seeing the full failure list on Linux").

Local reproduction (uncontended re-run needed -- see below) showed
dozens of F marks scattered from ~1% to ~45% of tests/unit alone before
this box's own heavy multi-agent CPU contention (load average 8-10 on a
12-core host, several sibling frob check/cargo processes) made a full
unscoped run unreliable to complete here. A clean, uncontended CI run
(or a dedicated local run with no sibling agents active) is needed to
get the authoritative failing-node-id list -- this repo's own
`SUITE-RESULT: exitstatus=... collected=... failed=...` line and the
pytest summary are the source of truth once obtained.

PLAN: once a clean full-suite run is available (CI, or a local run with
no contending agents), capture the complete list of FAILED node ids and
counts, triage each into its own bug ticket (or a small number of
tickets grouped by root cause) rather than fixing them inline here --
T-2980's acceptance was making the suite terminate and report, not
clearing this backlog. Cross-reference against T-2971 (macOS's
~144 uncharacterized failures) for overlap before assuming these are
new/distinct.