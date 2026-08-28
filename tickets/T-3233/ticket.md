---
id: T-3233
title: frob._cli_parsers --lang choices drifted narrower than frob.lang
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/**
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
T-2996 measured several --lang argparse choices lists (xref, cycle, check) hard-coded to ['python','cpp','c'], narrower than frob.lang.supported_languages() (9 languages). Measured, not fixed, in T-2996's scope.