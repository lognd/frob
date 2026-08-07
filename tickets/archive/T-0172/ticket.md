---
id: T-0172
title: managed marker for config-only infra nodes promised in surface.md but unimplemented
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- docs/strata/surface.md
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_node_managed_marker_elaborates_to_attr
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_node_without_managed_is_not_managed
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_store_managed_marker_elaborates_to_attr
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_non_managed_node_with_mismatched_boundary_still_fires
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_with_same_shape_discharges
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_still_requires_a_discharging_claim
- tests/unit/strata/test_managed.py::TestManagedTier2ImportConformance::test_managed_node_owned_files_produce_no_violation
- tests/unit/strata/test_managed.py::TestManagedTier2ImportConformance::test_non_managed_node_with_same_shape_still_violates
designated_repro_test: null
threat: null
component: null
---
logand.app pilot: docs/strata/surface.md names a planned managed marker for pure-config infrastructure nodes (e.g. a Caddyfile-configured edge) but the grammar does not implement it, so config-only nodes cannot be honestly modeled without fake code bindings. Same doc-grammar drift class as T-0166. Either implement managed (parse -> elaborate -> conformance treats the node as having no scannable code by declaration, with the audit reporting it as managed rather than unmodeled) or correct surface.md; doc and grammar must agree.