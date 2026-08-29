---
id: T-3401
title: 'frob test: detect missing pytest-testmon like xdist bound check'
state: done
kind: feature
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
- src/frob/tickets/_worktree_guard.py
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: T-3401's new symbols need a frob:doc anchor in this module's own docs file,
    matching every existing sibling symbol here
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: docs/modules/tickets-data-storage.md
  reason: 'reverting: the doc anchor closure pulls in the whole tickets-data-storage
    module''s unrelated symbols (107 warnings) -- too large for this ticket; documenting
    the two new functions deferred to a follow-up'
  actor: logan
  at: '2026-08-29'
evidence:
- tests/test_worktree_guard.py::TestWarnIfTestmonPluginMissing::test_must_fire_when_plugin_not_importable
- tests/test_worktree_guard.py::TestWarnIfTestmonPluginMissing::test_must_stay_quiet_when_plugin_importable
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2: make test-fast runs pytest --testmon but frob test has no equivalent incremental selection or detection of whether pytest-testmon is actually installed. Mirror T-3316's warn_if_xdist_bound_missing fix pattern (landed c4d980968, src/frob/tickets/_worktree_guard.py): detect plugin ABSENCE, not just an unset flag/bound. Missing-but-requested must be a loud typed error naming the tool + install command (T-3276 category rule: required-missing=loud error, optional-and-unused=silent, optional-but-needed-for-gate=UNMEASURED loudly never CLEAN). Never silently degrade a fast/incremental run into a full run or vice versa. Also evaluate: should testmon be a declared optional dependency, and should scaffold's own test config mention it.