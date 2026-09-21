---
id: T-5177
title: TICK014 doc anchor needs T-3899 land_commit-precedence update
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-data-storage.md
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
T-3899 changed TICK014 (src/frob/gates/_empty_diff_close.py::empty_code_diff_violations) to judge a closed ticket by its land_commit's own git-show diff (when recorded) instead of only the stored done-report Changed block. docs/modules/tickets-data-storage.md#tick014----empty-code-diff-on-close-t-3092 still describes only the original T-3092 Changed-block-only behavior. T-3899 could not update this doc itself: the file was leased by another in-progress ticket when T-3899 tried to add it to scope (frob ticket scope refused --add). Update the anchor's prose to document the land_commit precedence and the three edge cases T-3899's module docstring in _empty_diff_close.py decided (revert-after-land, concurrent-branch commits, never-landed fallback).