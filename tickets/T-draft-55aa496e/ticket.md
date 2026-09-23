---
id: T-draft-55aa496e
title: Checked-in _KNOWN_RULE_FIXABILITY literal missing DOCARCH002/DSTACK001/FMT002
  (landed rules never updated it)
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
- src/frob/gates/_fixability_scan.py
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
found while working T-4758: tests/gates_suite/test_sys.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan fails on dev -- generated_fixability() reports DOCARCH002/DSTACK001/FMT002 as auto-fixable but the checked-in _KNOWN_RULE_FIXABILITY literal (src/frob/gates/_fixability_scan.py) was never updated when those rules landed (T-4713/T-4714 and an earlier DOCARCH002 land). Pre-existing on dev, unrelated to T-4758's directive-comment-only sweep; confirmed by diff inspection (T-4758 never touches this file).