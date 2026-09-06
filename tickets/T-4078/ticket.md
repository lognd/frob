---
id: T-4078
title: 'M-9: rate-limit invariant for unauthenticated PII-returning routes'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design decision between a first-class route rate-limit construct and
    a frob:invariant binding an existing guard to a PII-returning handler, when this
    ticket's design step completes, then the smaller-change option is chosen if it
    covers the finding, and the reasoning is recorded
  evidence: []
- text: given an unauthenticated route returning a carries-declared PII field with
    no bound rate-limit guard, when frob check runs, then the new invariant fails
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
M-9 (F-273). VERIFIED: strata's SYS/REL families model capabilities and reliability attrs; a `rate 5 req/s` on a flow (e.g. flow f_browser_edge) is an EDGE property today, not a ROUTE property -- so a route can return PII to an unauthenticated caller with no rate limit at all, while the edge it happens to traverse carries an unrelated rate declaration that says nothing about THIS route specifically.

FINDING THIS WOULD HAVE CAUGHT: an unthrottled claim-preview endpoint returning carries-declared PII fields to an unauthenticated caller, invisible because rate limiting is modeled at the edge/flow level, not the route level, and the actual code-side convention (`_rate_limit_guard`) is just a naming convention nothing checks. Proposed: a strata-level or frob-level assertion that every route returning a carries-declared PII field to an unauthenticated caller declares a rate limit -- i.e. lift the existing `_rate_limit_guard` convention into a checked invariant rather than leaving it a convention nothing enforces.

FIRST STEP: confirm during design whether "route" needs to become a first-class strata construct with its own rate-limit attribute (a bigger change) or whether this can be expressed as a frob:invariant binding an existing route-registration site's guard usage to the PII fields its handler returns (a smaller change reusing existing binding machinery) -- prefer the smaller change if it covers the finding.
