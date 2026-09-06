---
id: T-4080
title: 'L-2: import.meta.env pattern for browser-side env.read'
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: low
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dangerous_ops_other.py
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
L-2 (F-273). VERIFIED: src/frob/vet/_capability_registry/_dangerous_ops_other.py registers "process.env" (Node-side env read) as env.read for typescript, but has no pattern at all for "import.meta.env" (Vite/browser-side build-time env access) -- confirmed missing, distinct gap from process.env's coverage. The scanner literally cannot express "the browser node read a build-time env var" because no pattern recognizes the syntax browser code actually uses for it.

FINDING THIS WOULD HAVE CAUGHT: this is the same FROBLEMS entry as L-1 in the consumer's own numbering (their scanner-gap report groups it with L-1) but a DIFFERENT underlying pattern gap -- import.meta.env reads (the mechanism H-2's Turnstile key defect and any other frontend build-time secret/config handling goes through) are invisible to the capability scanner entirely, so the browser node's env.read capability can never be declared or checked against anything it actually does.

Proposed: add an "import.meta.env" pattern to the typescript env.read (and env.write, for the `import.meta.env.X = ...` mutation shape, mirroring process.env's read/write pair already in the registry) entries in _dangerous_ops_other.py. Cheap, purely additive to the existing pattern table -- no new capability kind needed, env.read/env.write already exist.
