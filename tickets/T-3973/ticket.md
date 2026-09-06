---
id: T-3973
title: diagnosable tree-sitter query compile errors in policy.pattern
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a [[policy.pattern]] query that fails to compile due to field order,
    when policy is loaded, then the error message names the offending pattern, its
    node type, and the field-order issue rather than an opaque tree-sitter error
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3920 item 2. The consumer's own words: "the cheapest item here." VERIFIED: git grep confirms src/frob/policy/__init__.py is where tree-sitter Query objects are compiled for [[policy.pattern]] entries.

FINDING THIS WOULD HAVE CAUGHT: a [[policy.pattern]] tree-sitter query with field order that a given grammar is unforgiving about (a query using named fields in the wrong order for that node type), where the compile error surfaced does not say why the query failed to compile. The consumer had to bisect the query OUTSIDE frob by trial and error. Pure diagnosability: catch the underlying tree-sitter QueryError (or equivalent) at policy load time and re-raise/report with the offending pattern's source snippet, the node type involved, and (if determinable) the expected field order for that node kind -- so the author sees why, in-tool, instead of an opaque compile failure.
