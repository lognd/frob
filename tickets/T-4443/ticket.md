---
id: T-4443
title: 'LARGE001: _native_staleness.py at 805 lines after T-4434, extract the digest
  helpers'
state: in-progress
kind: bug
origin: agent
created: '2026-09-12'
priority: high
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_native_staleness*.py
- tests/unit/strata/test_native_staleness.py
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
CI run 34675057655 (head d0fc8ba1e, 2026-09-12), every leg: LARGE001: src/frob/strata/_native_staleness.py file has 805 lines (threshold: 800). T-4434's land (5ce34a4c8, +66 lines) pushed the file over the threshold; it was 739 lines before. Extract one cohesive helper group (the T-4434 tracked-content digest helpers, or the seeding/backdating block) into a sibling module such as src/frob/strata/_native_staleness_digest.py with its own docstring and frob:tests edges, keeping every public name importable from _native_staleness. ACCEPTANCE: (1) _native_staleness.py under 800 lines with headroom (at most 720); (2) tests/unit/strata/test_native_staleness.py still passes unchanged or with import-path-only edits; (3) frob check --ticket shows no LARGE001 on either file. Sprint v0.531.0 (CI green blocker). Quarantine finding LARGE001:src/frob/strata/_native_staleness.py (batch 5ce34a4c8) is disposed to this ticket.
