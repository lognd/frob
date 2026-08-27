---
id: T-3056
title: 'docs/strata/vmodel.md: update closure-rule prose for T-3043''s path-reachability
  fix and new rule 5'
state: done
kind: docs
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
scope:
- docs/strata/vmodel.md
- strata-core/src/graph/vmodel.rs
evidence_scope:
- tests/unit/strata/test_vmodel_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/vmodel.rs
  reason: 'T-3043 renamed the heading; the frob:doc anchor comments in vmodel.rs point
    at the old #the-four-closure-rules slug and must move with it or DOCANCHOR breaks
    -- narrow, mechanical anchor-string update only, no logic change'
  actor: logan
  at: '2026-08-27'
evidence:
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_satisfies_cycle_fires_through_vmodel_check
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: cd51fcd127dac73d31205310bb503b99051619fc
---
V-model docs/strata/vmodel.md's closure-rule prose ("every artifact node
must have >=1 incoming/outgoing edge of kind X") is stale relative to
T-3043's fix: rules 1/2 now require the closure to CONTAIN a real
boundary-level node (innermost/outermost), and a new rule 5
(check_no_trace_cycle) exists and is undocumented. docs/strata/vmodel.md
was excluded from T-3043's scope because it was leased by in-progress
T-3009 at the time. Update the "The four closure rules" section to state
the corrected semantics and add rule 5, once T-3009 releases the lease.