---
id: T-3260
title: Split oversized V-model files under LARGE001 (T-3044 growth)
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/vmodel.rs
- strata-core/src/parse/grammar_core.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3079's post-land sweep re-measurement confirmed strata-core/src/graph/vmodel.rs (992 lines) and strata-core/src/parse/grammar_core.rs (831 lines) are genuinely over the 800-line LARGE001 threshold, both grown past it by T-3044 (V-model H3). T-3079 waived both findings (frob:waive LARGE001) to unblock the sweep-regression ticket rather than doing a real split inline. This ticket is the deferred real fix: split vmodel.rs's closure-rule logic and grammar_core.rs's parse_vmodel_node/parse_vmodel_edge into their own modules, then remove the waivers.