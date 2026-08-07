---
id: T-1059
title: 'detector: frob ticket start warns when worktree is N+ commits behind main
  tip'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_leases.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: wiring warn_if_worktree_stale needs a test file and doc anchor outside src/frob/tickets/**
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: wiring warn_if_worktree_stale needs a test file and doc anchor outside src/frob/tickets/**
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_warns_when_behind_threshold
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_when_within_threshold
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_on_non_git_root
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_respects_configured_threshold
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_returns_default_when_frob_toml_absent
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_reads_configured_value
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_non_positive_value_falls_back_to_default
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_malformed_toml_falls_back_to_default
designated_repro_test: null
threat: null
component: null
---
T-1030 investigated why dispatched agent worktrees were repeatedly cut from
a stale base (fa606fe8/b3589c3e). Root cause: the EnterWorktree harness
tool's default worktree.baseRef=fresh branches new worktrees from
origin/<default-branch>, and this clone's origin/main has not been kept in
sync with local main (observed 81 commits behind at investigation time).
This is harness-side behavior, outside frob's codebase, and cannot be
fixed by editing frob source.

Add a frob-side detector: frob ticket start (and/or frob check) warns
loudly when the worktree's merge-base with local main is more than N
commits behind main's current tip, pointing at the playbook's warm-up
section (docs/guides/agent-playbook.md#1-worktree-warm-up). This does not
prevent the stale cut but catches it immediately at the start of a
ticket instead of silently carrying it through a whole session.