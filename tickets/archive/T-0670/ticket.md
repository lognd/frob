---
id: T-0670
title: 'strata: binding-totality + effect-conformance - reject logic laundered into
  an unbound file'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
parent: T-0341
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106
designated_repro_test: null
acceptance:
- text: Given dangerous logic moved into a helper module not directly bound to any
    node but reachable from a bound node, when checked, then the effect is still attributed
    and conformance-checked, not silently dropped
  evidence:
  - tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
threat: null
component: null
---
Extend SYS100/SYS101/SYS102 so the bound-set is provably total against the capability graph: a module reachable via import/call from a bound node but itself unbound must not silently escape effect-conformance checking -- closes acceptance-criterion (4) 'binding need not be total, so logic can be laundered into an unbound file'.