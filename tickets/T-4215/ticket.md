---
id: T-4215
title: 'gate: a dynamically-resolved import/reference resolving to a path unreachable
  from the shipped artifact is a finding, not an accepted OPAQUE001 waiver'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4157
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_opaque.py
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
Consolidates T-4157/H4-1 second half (a JS @vite-ignore dynamic import whose specifier resolves under src/ but is not reachable from the built output; cheaply approximated as 'no built artifact may contain the literal /src/') with T-4175/P2 (the same shape via a Python importlib string-target and a Dockerfile COPY operand -- 'the target module genuinely does not exist yet' legitimised by an OPAQUE001 waiver). Same underlying question across three runtimes: does a dynamically-resolved specifier land somewhere the shipped artifact actually contains. Adjacent to T-4160 (also OPAQUE001, opposite defect: a false POSITIVE on a type-position import) -- different mechanism, same gate file, worth sequencing together. Not fixture-testable in frob's own tree: no bundler/Docker build target exists here.