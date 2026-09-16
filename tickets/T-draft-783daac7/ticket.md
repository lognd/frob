---
id: T-draft-783daac7
title: C# and Unity support for frob (owner directive 2026-09-16)
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-CSUNITY-EPIC/**
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
Owner directive 2026-09-16: bring C# to end-to-end parity and add Unity support (Unity project model, .NET BCL + Unity API capability maps, NUnit/UnityTest evidence, fixture project). See design doc / stories for measured starting state: no C# capability resolver wired into _capability_scan.py, no NUnit/UnityTest collector, T-3232/T-3234/T-3856 are prerequisite cross-cutting bugs (linked, not duplicated), T-1597/T-1598 are the general umbrella (not duplicated -- this epic pulls C#/Unity out of that backlog per owner priority).