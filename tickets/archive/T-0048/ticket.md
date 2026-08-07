---
id: T-0048
title: strata charter + design doc tree under docs/strata/
state: done
kind: docs
origin: human
created: '2026-07-17'
priority: medium
parent: T-0047
tier: ticket
sprint: null
scope:
- docs/strata/**
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
designated_repro_test: null
acceptance:
- text: GIVEN the doc tree WHEN frob check runs THEN DOC001 passes and every strata
    page is reachable from docs/index.md
  evidence: []
threat: null
component: null
---
Write charter.md (north star, laws, decisions), kernel.md, surface.md, evidence.md, policy.md, boundary.md, roadmap.md. All decisions from the design sessions recorded unambiguously; strata name final; engine independent of lithos with its own strata-core crate.