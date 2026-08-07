---
id: T-0060
title: strata elaborator framework + std.trust vocabulary
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0049
parent: T-0050
tier: ticket
sprint: null
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_elaborate.py::TestElaborateFullMapping::test_maps_every_construct_field_for_field
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_duplicate_node_id_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_boundary_referencing_unknown_flow_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateAbstract::test_abstract_marker_preserved_in_attrs
- tests/unit/strata/test_elaborate.py::TestElaborateEndToEnd::test_parse_elaborate_evaluate_matches_expected_verdicts
designated_repro_test: null
threat: null
component: null
---
Vocabularies are pure functions surface->kernel facts; the prover never learns domain words. std.trust: lattices, principals, components, channels, endorse/declassify boundaries.