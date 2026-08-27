---
id: T-3043
title: 'V-model H2: the four closure rules check local edge degree, not path closure
  -- a mutual-satisfies pair with zero requirements passes all four'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/vmodel.rs
- strata-core/src/lib.rs
- tests/unit/strata/test_vmodel_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/vmodel.rs
  reason: 'fix closure rules to check path-reachability to a real requirement/design
    endpoint instead of local edge degree, and wire find_cycle into check_closure;
    lib.rs needs the new ClosureViolation variant mapped in vmodel_check (docs/strata/vmodel.md
    excluded: leased by in-progress T-3009)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/lib.rs
  reason: 'fix closure rules to check path-reachability to a real requirement/design
    endpoint instead of local edge degree, and wire find_cycle into check_closure;
    lib.rs needs the new ClosureViolation variant mapped in vmodel_check (docs/strata/vmodel.md
    excluded: leased by in-progress T-3009)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: 'new pytest evidence that actually exercises vmodel_check end-to-end via
    the Python binding (T-3043: T-3005/T-3007 evidence-laundering lesson -- do not
    bind evidence that does not touch the changed code)'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_mutual_satisfies_pair_with_zero_requirements_now_fires
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_genuine_four_level_chain_is_quiet
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_satisfies_cycle_fires_through_vmodel_check
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: acd6aa358b64d38efeddbb793e4d8fd9760052cd
---
