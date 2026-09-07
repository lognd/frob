---
id: T-4149
title: decide and document the no-[[test.runner]]-declared fallback policy
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
T-3887's open question: what happens when a project declares no [[test.runner]] and has no resolvable environment for project_tool_argv/pytest spawns. Options: refuse the affected gates with a clear message, or fall back to frob's own interpreter WITH an explicit, unmissable capability statement that the result is measured in frob's environment (never a silent fallback). Decide, document in docs/modules/process.md and docs/modules/testing.md, and add a MUST-FIRE fixture.