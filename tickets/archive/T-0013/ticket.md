---
id: T-0013
title: Raise min_unit_cases from 1 back to 3
state: dropped
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
frob.toml's [testing] min_unit_cases was dropped from the 3-case aspirational target to 1 to unblock the gates dogfood milestone (TEST002 fires thousands of times on legacy surface otherwise). Raise it back to 3 once the new core modules (lang/graph/tickets/gitio/testing/gates/policy) have real multi-case unit coverage, then extend to the rest of the codebase.

DEFERRED BY DESIGN: raise min_unit_cases to 3 makes frob's OWN gates stricter. frob is
a churning 0.1.0a0 alpha; the feature (severity dial / convention
inference) ships and works -- adopting max strictness on frob itself is
a project-maturity decision for post-alpha, not a build task. Same
reasoning as not committing .frob-release.json.