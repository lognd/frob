---
id: T-2842
title: Malformed frob:waive LARGE001 directive in _patterns.py (embedded escaped quotes
  break the parser)
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_patterns.py
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
T-2359 landed a frob:waive LARGE001 directive on src/frob/arch/_patterns.py:129 whose reason text contains an embedded escaped double-quote (severity=\"suggestion\"), which the waiver-directive parser cannot handle -- "frob check" logs a WARNING malformed directive: bad attribute syntax for it on every run, and the LARGE001 waiver on this file is therefore NOT being applied via this mechanism (need to verify whether it still resolves some other way). Fix: rephrase the reason text to avoid embedded double quotes (or single-quote/otherwise escape per this repo convention), matching how other multi-clause waiver reasons in this repo avoid the same trap. Found while working T-2841 (I001 fix) -- frob check --json surfaced this WARNING repeatedly, unrelated to that scope.