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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense cache-vs-cdn boundary narrative into T-0845 body
  actor: logan
  at: '2026-09-19'
  old_length: 544
  new_length: 1956
evidence:
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_node_and_fill_flow
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_cache_fill_and_invalidation_flows_are_local_exempt
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The two REL200 waivers on design/frob.strata's graph_cache__fill and graph_cache__inval_f_parse flows exist because elaborator-synthesized in-process cache flows have no attr-forwarding surface: there is no way to declare (or discharge) a timeout/local disposition on a flow the elaborator invents. Add that surface (per-flow attr forwarding from the synthesizing rule, or an explicit local disposition for in-process in-memory flows), then burn down both waivers. Deferred from T-0640 at its salvage-close; the waivers' ticket refs point here.

<!-- narrative-moved:src/frob/strata/_infra.py:84:T-0845 -->
: Flow attr marking a `cache`'s elaborator-synthesized fill/invalidation
: edges as explicitly NOT crossing a real process/service boundary
: (T-0845, the SAME bare-marker literal `_reliability.py::_LOCAL_ATTR`
: reads to exempt a flow from the REL200 TIMEOUT obligation -- kept as a
: local copy, not an import, for the same cross-module-vocabulary reason
: `_MANAGED_ATTR` above documents). This is a deliberate, unconditional
: disposition for the `cache` construct specifically (NOT `cdn`): per
: docs/strata/surface.md#key-construct-semantics, `cache X of Y` is
: std.infra's IN-PROCESS derived view -- its node inherits `Y`'s own
: trust directly (`_cache_node_and_fill_flow` below) rather than a
: separate provider trust the way `cdn`'s network-fronting variant does
: (`_cdn_node_and_fill_flow`, which deliberately does NOT get this attr).
: `cache` therefore has no real cross-boundary hop to time-bound in the
: first place, for EVERY declaration of it, not just this repo's own
: `graph_cache` -- this is the "explicit local disposition for
: in-process in-memory flows" T-0845 chose over a per-flow `attr`
: grammar clause, since `cache`'s parser (`strata-core::parse_cache`)
: has no such clause and adding one is a strata-core change outside this
: ticket's scope (src/frob/strata/**, design/frob.strata,
: tests/unit/strata/** only).