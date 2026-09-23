---
id: T-5392
title: 'Post-land sweep residue 2026-09-23_0821: DUP002:src/frob/lang/_walk_css.py
  FLAGCOV001:frob.toml '
state: done
kind: bug
origin: human
created: '2026-09-23'
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
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_css.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/_walk_css.py
  reason: DUP002 fix on _walk_css.py; FLAGCOV001 half resolved by T-5389
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
body_changes:
- mode: append
  reason: BUG002 needs explicit no-behavior-change declaration for a waiver-only fix
  actor: logan
  at: '2026-09-23'
  old_length: 201
  new_length: 312
evidence:
- tests/test_lang_css.py::TestCss::test_top_level_rule_set_is_a_class_symbol
- tests/test_lang_css.py::TestScss::test_top_level_rule_set_is_a_class_symbol
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5392
branch: t-5392
---
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
DUP002:src/frob/lang/_walk_css.py
FLAGCOV001:frob.toml

frob:no-behavior-change reason="DUP002 waiver comment only -- no runtime behavior change to _css_rule_symbol"