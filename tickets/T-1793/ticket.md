---
id: T-1793
title: Update docs/modules/perf.md's T-1578 section for T-1620's strata_core widening
state: queued
kind: docs
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1620 widened `_perf_reach_degraded_marker`'s native-staleness check from
`frob_core` only to both `frob_core` and `strata_core` (measured
2026-08-05 incident: a stale strata_core silently zeroed PERF004
repo-wide while the frob_core-only marker reported healthy).
docs/modules/perf.md#perf-reach-native-staleness-signal-t-1578 was not
updated because docs/modules/perf.md is outside T-1620's declared scope
(src/frob/gates/**, src/frob/perf/**, src/frob/app/ticket_runner/
_land_cmd.py, tests/test_gates_ratchet.py, docs/modules/gates.md).

The section's prose now has two specific inaccuracies:
- "resolve their call graph through frob.graph.callgraph's native
  frob_core fast path" and the claim that PERF001-004 "need no native at
  all and stay fully trustworthy" -- true for the REACH analysis
  specifically, but every perf rule's parsed INPUT (frob.lang.parse_file,
  called from _perf_gate_parse_files before perf_rules ever runs) goes
  through strata_core's tree-sitter grammar, so PERF001-004 are NOT
  independent of native staleness the way the current prose implies.
- `_PERF_REACH_NATIVE_NAME` (singular) no longer exists; it is now
  `_PERF_REACH_NATIVE_NAMES` (a frozenset of both native names).

docs/modules/gates.md's own T-1578 section (in T-1620's scope) has
already been updated with the corrected explanation and can be used as
the reference text -- this ticket is the perf.md-side mirror update.
