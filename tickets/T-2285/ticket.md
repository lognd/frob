---
id: T-2285
title: Extend T-2280's file-local pre-land error gate to DOC005/SELFAUDIT001/ARCH103
state: queued
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2280 generalized T-2214's does-not-worsen land-time gate to a severity-derived registry of FILE-LOCAL ERROR checkers (RENDER001 registered). Three rules named in T-2280's own measured evidence (RENDER001 1->4, SELFAUDIT001 1->3, DOC005 2->3, ARCH103 2->3) do NOT fit the file-local (current-content vs merge-base-content, two small parses) shape: DOC005 targets README.md/the CLI table specifically and compares against the parser tree, not the file's own prior content; SELFAUDIT001 evaluates frob's own design/compliance state, not any particular touched file; ARCH103 needs the repo-wide call graph for SRP/cohesion classification. Bringing these under land-time coverage needs either (a) a bounded, cheap way to compute each without a full analyze_project/GraphSnapshot build, or (b) accepting a different, still-bounded cost model than T-2280's two-parses-per-file one. Scoped follow-up, not a widening of T-2280 itself.