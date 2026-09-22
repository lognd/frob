---
id: T-5291
title: test_strata_tmlanguage.py grammar/keyword bidirectional coverage drifted
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_strata_tmlanguage.py
- strata-core
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gh run 35717833933; re-verified on dev tip 3acf8c6b30: test_construct_keywords_match_parser_bidirectionally and test_clause_keywords_covered_by_grammar both fail -- tmLanguage grammar and parser keyword sets have drifted apart.