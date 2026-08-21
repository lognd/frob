---
id: T-2799
title: wire frob_core.py_function_metrics into archgate's per-function metrics walk
state: in-progress
kind: feature
origin: human
created: '2026-08-21'
priority: high
parent: T-2790
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_python.py
- tests/unit/test_arch_python_native.py
- tests/unit/test_arch.py
- docs/audits/perf.md
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: 'AFFECT001: T-2799''s new symbols (_native_metrics_available/_native_metrics_by_span/_py_collect_catches_and_subscripts/_events_from_native)
    fall in NormalizedModule''s affects-closure; documenting the native dispatch there
    closes the finding'
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2790's profile measured archgate's per-function metrics extraction
(_py_build_module/_py_build_function/_py_collect_body_events/_iter_own_
scope) at 31% of archgate's own cost (73.40s of 236.34s profiled, matching
T-1222's own done-report figure exactly). T-1222 (archived, done) already
built and golden-tested frob_core.py_function_metrics as a byte-identical
Rust replacement for exactly this walk, but it has zero call sites under
src/frob/ today -- built, tested, documented, never wired to a caller.

Plan: dispatch _py_build_function/_py_build_module to
frob_core.py_function_metrics when frob_core is available (same
availability-check pattern T-0953's _near_duplicate_cluster_native
dispatch already uses), falling back to the existing pure-Python path
otherwise, byte-identical output either way.

Hard requirement: a real, unbudgeted frob check run on this repo must
report an IDENTICAL finding count before and after (per T-2790's own
constraint) -- a speedup that changes the finding count is a behavior
change, not this ticket. Also required: a positive control -- plant a
long-function/god-class/deep-nesting violation and confirm it fires
identically through the native path before wiring it as the default.

See docs/investigations/T-2790-check-stage-profile.md for the full
profile this ticket is drawn from.