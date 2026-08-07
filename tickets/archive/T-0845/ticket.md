---
id: T-0845
title: 'strata: attr-forwarding surface for elaborator-synthesized in-process cache
  flows (REL200 waiver burn-down)'
state: done
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: T-0640
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_node_and_fill_flow
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_cache_fill_and_invalidation_flows_are_local_exempt
designated_repro_test: null
threat: null
component: null
---
The two REL200 waivers on design/frob.strata's graph_cache__fill and graph_cache__inval_f_parse flows exist because elaborator-synthesized in-process cache flows have no attr-forwarding surface: there is no way to declare (or discharge) a timeout/local disposition on a flow the elaborator invents. Add that surface (per-flow attr forwarding from the synthesizing rule, or an explicit local disposition for in-process in-memory flows), then burn down both waivers. Deferred from T-0640 at its salvage-close; the waivers' ticket refs point here.