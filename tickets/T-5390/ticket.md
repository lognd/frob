---
id: T-5390
title: Wire html/javascript/vue into capability/dup/docblock FACETS
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
- src/frob/lang/_support.py
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
found while working T-5300: html/javascript/vue get a real frob.lang grammar/walker (_walk_html.py/_walk_javascript.py/_walk_vue.py) but, like css/scss before them (T-5303, T-5386), are not yet wired into the capability/dup/docblock FACETS registry -- follow-up, not this leaf's scope.