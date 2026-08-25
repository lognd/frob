---
id: T-2799
title: wire frob_core.py_function_metrics into archgate's per-function metrics walk
state: in-progress
kind: feature
origin: human
created: '2026-08-21'
priority: high
blocked_by:
- T-draft-567dc170
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
land_commit: c51eed0f11e47df5fe9cdd3a6d02b6d1b6d4c59d
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

## Failure log
- 2026-08-21 attempt 1: MEASURED NET SLOWDOWN, do not re-attempt as scoped. Wiring frob_core.py_function_metrics (T-1222) into _py_build_function/_py_build_module makes archgate 30-70 percent SLOWER: native-ON averaged 27-45s vs native-OFF 21-30s, alternating order, 6+ trials per side, controlled for fleet-load noise (2026-08-21). Root cause: the native kernel's catches/subscripts output is narrower than NormalizedCatch.exception_types and NormalizedSubscript.is_slice require (T-2539), both feeding real may-raise resolution, so a compensating _py_collect_catches_and_subscripts walk is mandatory -- that walk plus PyO3 marshalling of every event into fresh Python objects costs more than the Rust walk saves. Correctness was NOT the problem: byte-identical NormalizedModule output verified across 4 corpora, and T-1222's parity tests pass unmodified. Changes were fully reverted to byte-identical pre-ticket state. BLOCKED ON: extending the Rust kernel itself to carry exception_types/is_slice so the compensating walk can be dropped (follow-up filed under parent T-2790). Any future attempt must re-measure with the same A/B methodology rather than assume the fix wins.
- 2026-08-25 attempt 4: Attempt 2 (2026-08-25): confirmed attempt 1's root cause by reading frob-core/src/arch_python.rs and frob_core.pyi directly -- catches carry only a single exception_type (str|None), never the exception_types tuple NormalizedCatch/T-2539 need for multi-type except clauses, and subscripts carry only a bare line with no is_slice bool. Both gaps force the same compensating Python walk attempt 1 measured as net-slower than the pure-Python path it replaces. No new dispatch strategy found within this ticket's Python-only scope that avoids the compensating walk. Filed T-draft-567dc170 (parent T-2790) to extend the Rust kernel itself and blocked T-2799 by it -- re-attempt once that lands, with the same A/B methodology.
