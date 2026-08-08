---
id: T-1623
title: 'strata maturity: make capability enforcement watertight'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/strata/**
- src/frob/vet/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Umbrella for the strata self-model hardening reviewed on 2026-08-05. Findings, in dependency order: the declaration file is half redundancy (duplicate attr blocks, 5277 test names declared as interface); interface= is a generated mirror that cannot be meaningfully violated; capability detection is lexical rather than symbol-resolved; and via grants whole FILES rather than single controllable locations, with permission lists that only ever grow. Children carry the detail. Sequence the mechanical cleanups first so the design work reasons over a smaller surface.