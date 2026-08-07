---
id: T-0016
title: Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0001
parent: null
tier: ticket
sprint: null
scope:
- src/frob/map/**
- src/frob/outline/**
- src/frob/xref/**
- src/frob/cycle/**
- src/frob/dup/**
- src/frob/ast/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_integration.py::test_cycle_detected_in_mini_project
designated_repro_test: null
threat: null
component: null
---
Re-platform map/outline/xref/cycle/dup onto frob.lang's uniform ParsedFile contract, then delete src/frob/ast. Deferred post-0.1.0; blocked_by T-0001 since dup's re-platform is entangled with the frob-core work.