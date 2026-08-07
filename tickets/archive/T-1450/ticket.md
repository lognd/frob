---
id: T-1450
title: 'strata: SYS101 staleness judged per may-via surface, not whole-node kind'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_via_scoped_grant_stale_while_other_surface_uses_same_kind
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_via_less_grant_alongside_via_grant_still_discharges_whole_node
designated_repro_test: null
threat: null
component: null
---
T-1440 parent: (3) SYS101 staleness per via surface. The design sketch's
item 3: "SYS101 staleness likewise judged per via surface, so a dead
grant on one file is flagged even while another file legitimately uses
the same kind." The T-1440 landing delivers grammar + model plumbing
(MayGrant/MayGrantDecl carrying via globs) and the per-file SYS100 join
(_effects.py::_declared_kinds_for_file / check_capability_conformance)
but NOT this per-surface staleness check -- `_stale_design_violations`
(the SYS101 producer, `_selfconform.py`) still judges staleness at the
whole-node kind level, so a grant scoped to file A that only file B ever
exercised still reads as "used somewhere on the node", not stale on A
specifically. Plan: extend the SYS101 join to iterate per-MayGrant (not
per-kind-on-node): a grant with `via` is stale iff none of its own via
surface's observed kinds match; a via-less grant keeps today's whole-node
join. Needs new/adjusted evidence in the mutation-audit harness
(`_mutation_audit.py`) to keep `test_baseline_sys101_is_zero` meaningful
under the new per-surface semantics.