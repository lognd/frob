---
id: T-0266
title: SYS100 core+extended can report the same undeclared-capability site twice
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCrossPassDedup::test_same_site_observed_by_both_passes_yields_one_finding
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCrossPassDedup::test_dedupe_helper_drops_extended_when_core_already_reports_same_site
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCrossPassDedup::test_dedupe_helper_keeps_distinct_node_or_capability_sites
designated_repro_test: null
threat: null
component: null
---
Filed while working T-0209 (re-filed after a ledger-conflict drop). check_self_conformance's SYS100 join: _core_undeclared_violations (THREAT004 delegate, line=0) and _extended_kind_violations (T-0169 eval/env/ffi slice, real line via _effects.py) can each independently emit a SYS100 for the same (node, capability_kind), so one observed-but-undeclared capability surfaces as two findings. Dedupe by (node, capability_kind) [or (file,line,kind) once core tracks a line] before returning; regression fixture with one capability both paths flag.