---
id: T-draft-2c8aa622
title: Widen _a11y_gate file walk to include CSS/SCSS
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_a11y_gate.py
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
found while working T-5321: frob.gates._a11y_gate._A11Y_EXTENSIONS only covers html/vue/jsx/tsx, so frob.webapp._a11y_interaction's four CSS-declaration rules (A11Y117/120/121/122) are fully implemented and unit-tested but never actually invoked through the real gate (CSS files are never parsed/handed to any hook). Widen _A11Y_EXTENSIONS to include .css/.scss (frob.lang already parses both via T-5303) so these rules fire in frob check.