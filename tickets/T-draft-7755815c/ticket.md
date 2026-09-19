---
id: T-draft-7755815c
title: 'frob-suggest: replace blanket FROB_SUGGEST_ACK with per-rule token, update
  docs'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: T-draft-8c7e665d
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/*
- tests/test_hook_frob_suggest.py
- docs/guides/*
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: blanket FROB_SUGGEST_ACK=1 is replaced by a per-rule allow FROB_SUGGEST_ALLOW=<rule-id>
    that only suppresses that rule
  evidence: []
- text: paste-ready 'prefix it with FROB_SUGGEST_ACK=1 up front' wording is removed
    from every block message
  evidence: []
- text: a stale FROB_SUGGEST_ACK=1 prints a one-line notice and is ignored (not honored
    as a bypass)
  evidence: []
- text: repo-shipped docs describing the ack (agent playbook or equivalent) are updated
    in the same change
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 3 of T-draft-8c7e665d. See scratchpad/HOOK-AUDIT.md section 3.2.