---
id: T-3702
title: 'frob-timeout-guard: misplaced frob:doc on private _HELP_OR_DRY_RUN_RE'
state: done
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-timeout-guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-3702's fix has no test-visible behavior change; add the T-1616 marker
    so BUG002 requires the repro to PASS at parent rather than fail
  actor: logan
  at: '2026-09-02'
  old_length: 500
  new_length: 684
evidence:
- tests/test_hook_frob_timeout_guard.py::test_ticket_new_help_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_check_help_is_not_blocked
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3695 landed a frob:doc docs/guides/claude-hooks.md#frob-timeout-guardpy directive directly above the private _HELP_OR_DRY_RUN_RE constant instead of on main (or omitting it) -- gate:COV COV007 now flags it: 'frob:doc on private symbol .claude/hooks/frob-timeout-guard.py::_HELP_OR_DRY_RUN_RE -- doc anchors normally cover the public API surface'. Move the frob:doc directive onto main (which already carries one, so this one is likely just redundant/misplaced) or drop it from the private constant.

frob:no-behavior-change reason="removing a redundant frob:doc directive comment above a private constant; no functional/runtime change, main already carries an equivalent doc anchor"