---
id: T-draft-ab10a63c
title: 'Test evidence: NUnit + Unity Test Framework collection and runners'
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-draft-e7dd275c
parent: T-draft-783daac7
tier: story
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_csharp.py
- src/frob/testing/_runners.py
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
Story: collect and run C#/Unity tests as evidence bindable by frob:tests directives. Parent for the two leaves below. blocked_by T-draft-e7dd275c because the Unity-vs-plain-C# distinction (asmdef, test assembly) needs project-model detection to route correctly.