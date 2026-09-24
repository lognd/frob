---
id: T-draft-d335f78d
title: 'SELFAUDIT001 effect pre-filter is lexical: string literals naming a sink count
  as exec call sites'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Measured 2026-09-23 (T-5309 land refusal): SELFAUDIT001 reported capability 'exec' at src/frob/webapp/_websec_deser.py:419 and :438, where the only text was an f-string finding MESSAGE describing a sink shape (`os.system(...)`, `subprocess.{name}(..., shell=True)`). No call exists; `frob.strata._effects`' exec pre-filter is a substring scan over source text, so a string literal that names a sink counts as a call site. The agent had to split the literal (`"os" + ".system"`) to land, which is the lexical dodge the owner directive forbids on the checker side.

Fix: the exec/net/fs effect pre-filter must decide from parsed call nodes (tree-sitter / ast Call with the resolved callee), never from substrings; string and comment tokens are excluded by construction. Add a positive control (a real os.system call is reported) and a MUST-STAY-QUIET control (the same text inside a string literal is not). Then revert T-5309's literal split.
