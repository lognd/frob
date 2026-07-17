---
id: T-0013
title: Raise min_unit_cases from 1 back to 3
state: queued
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- frob.toml
evidence: []
attachments: []
---
frob.toml's [testing] min_unit_cases was dropped from the 3-case aspirational target to 1 to unblock the gates dogfood milestone (TEST002 fires thousands of times on legacy surface otherwise). Raise it back to 3 once the new core modules (lang/graph/tickets/gitio/testing/gates/policy) have real multi-case unit coverage, then extend to the rest of the codebase.