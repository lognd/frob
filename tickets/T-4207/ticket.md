---
id: T-4207
title: BUG002/EvidenceConfirmatoryOnly must exempt classes of tickets that structurally
  cannot demonstrate a local red state
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
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
Consolidates F-324 (a docs-only correction, kind=bug because the doc was wrong, refused as confirmatory-only because the same test passes before and after -- true for every doc-only bug) and F-387/T-0412 (a live-deployment-only prodtest assertion, same refusal, no local repro is possible). Add a kind: docs bug-of-documentation exemption, or exempt tickets whose diff is docs/spec-only or whose only assertion is inherently non-local, instead of a routine hand-waiver every time. Same source file as T-4168 (a different BUG002 detection gap) -- sequence after it to avoid a scope collision, no hard dependency. Fixture-testable: YES.