---
id: T-5171
title: Wire COV009 (shared frob:doc anchor review) into frob check dispatch + registry
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
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
T-4254 built COV009 (frob.gates._docblocks_refs.cov009_violations/
cov009_gate) fully self-contained and fixture-tested, but could not wire
it into frob check itself: src/frob/gates/__init__.py's dispatch table
(_assemble_gate_report) and src/frob/gates/_waive.py's _KNOWN_GATE_RULES
registry both needed a touch, and both files carried a live T-4540
lease at the time T-4254 was scoped.

Follow-up:
1. Add "COV009" to _KNOWN_GATE_RULES in src/frob/gates/_waive.py.
2. Wire `*cov009_gate(st.root, st.snapshot)` into
   frob.gates.__init__._assemble_gate_report's dispatch, alongside the
   other WAIVE00*/land-time self-checks (cov009_gate already computes
   its own working_diff(root, "main"), mirroring _land_format.
   land_format_gate -- no extra state from _GateInputs needed).
3. Add a COV009 row to docs/modules/gates.md's rule catalog table plus
   "COV009" to the frob:enumerates members= list at the top of that
   file.
4. Re-run tests/gates_suite/test_docblocks_refs_cov009.py plus a new
   end-to-end `frob check` fixture confirming COV009 actually fires
   through the real dispatch path, not just the direct function call.
