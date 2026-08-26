---
id: T-2908
title: 'frob-suggest: three nudge rules misfire and tax every agent call with a retry'
state: done
kind: bug
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-suggest.py
- tests/test_hook_frob_suggest.py
- docs/guides/claude-hooks.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/frob-suggest.py
  reason: fix three misfiring nudge rules and add must-stay-quiet fixtures
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: fix three misfiring nudge rules and add must-stay-quiet fixtures
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: frob:doc target for frob-suggest.py::main
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_hook_frob_suggest.py::test_floor_count_stays_quiet_when_grepping_a_rule_id
- tests/test_hook_frob_suggest.py::test_find_name_still_fires_unscoped_at_repo_root
- tests/test_hook_frob_suggest.py::test_find_name_stays_quiet_when_scoped_to_a_subdirectory
- tests/test_hook_frob_suggest.py::test_raw_worktree_still_fires
- tests/test_hook_frob_suggest.py::test_raw_worktree_no_longer_recommends_enterworktree
- tests/test_hook_frob_suggest.py::test_hand_edit_ledger_still_fires_on_the_real_ledger
- tests/test_hook_frob_suggest.py::test_hand_edit_ledger_stays_quiet_on_an_unrelated_file
- tests/test_hook_frob_suggest.py::test_recursive_grep_still_fires_unscoped_at_repo_root
- tests/test_hook_frob_suggest.py::test_recursive_grep_stays_quiet_when_scoped_to_a_subdirectory
- tests/test_hook_frob_suggest.py::test_floor_count_still_fires_on_a_genuine_counting_pipeline
designated_repro_test: tests/test_hook_frob_suggest.py::test_hand_edit_ledger_stays_quiet_on_an_unrelated_file
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 43f9aa7ac352599d0f9580abb607da781d80ca33
---
