---
id: T-3391
title: Make LEXCHECK001 detector check symbols, not regex/substring text
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_comment_placement.py
- tests/gates/test_comment_placement.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates/test_comment_placement.py
  reason: test coverage for symbolic rework
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LEXCHECK001 flags scan_cplace001_waive_reason_length and scan_cplace002_docs_narrative for deciding facts from regex/substring match with no symbol reference. Standing repo directive: checks must parse and compare SYMBOLS, not lexical text. Rework these two scanners to use the parser/AST instead of regex. Part of PyPI release error-floor burn (Series EQ slice).