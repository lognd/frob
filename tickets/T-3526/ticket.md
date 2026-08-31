---
id: T-3526
title: Killed frob check --fix leaves a silent half-applied Tier-A rewrite (deleted
  _build_parser, broke the CLI); make the fix pass transactional/journaled
state: in-progress
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
- src/frob/gates/_fix_engine_shared.py
- src/frob/gates/_fix_engine.py
- tests/unit/test_check.py
- tests/unit/test_fix_engine_journal.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: T-3526 only touches the manifest-journal infra, apply_tier_a_fixes loop,
    and check's pre-dispatch integrity checks; new fixture file for the abandoned-journal
    must-fire test
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_fix_engine_shared.py
  reason: T-3526 only touches the manifest-journal infra, apply_tier_a_fixes loop,
    and check's pre-dispatch integrity checks; new fixture file for the abandoned-journal
    must-fire test
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: T-3526 only touches the manifest-journal infra, apply_tier_a_fixes loop,
    and check's pre-dispatch integrity checks; new fixture file for the abandoned-journal
    must-fire test
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/check/__init__.py
  reason: T-3526 only touches the manifest-journal infra, apply_tier_a_fixes loop,
    and check's pre-dispatch integrity checks; new fixture file for the abandoned-journal
    must-fire test
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_check.py
  reason: T-3526 only touches the manifest-journal infra, apply_tier_a_fixes loop,
    and check's pre-dispatch integrity checks; new fixture file for the abandoned-journal
    must-fire test
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_fix_engine_journal.py
  reason: T-3526 only touches the manifest-journal infra, apply_tier_a_fixes loop,
    and check's pre-dispatch integrity checks; new fixture file for the abandoned-journal
    must-fire test
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
INCIDENT (series X, 2026-08-31, during T-3516 work): a `frob check --fix`
(unscoped Tier-A pass) that was KILLED mid-run (shell timeout) left
uncommitted, half-applied edits across ~14 unrelated files in the worktree
-- TWICE in one session -- including deleting `_build_parser` from
src/frob/_cli_parsers/_root.py, which broke the `frob` CLI entirely until
`git checkout --` reverted the strays. None of it reached a landed commit,
but only because the operator noticed.

DEFECT: the Tier-A fix engine mutates files in place as it goes, so a kill
at any point leaves an arbitrary prefix of the rewrite applied with no
marker, no journal, and no way to distinguish "operator edit" from
"abandoned auto-fix". The repo's own doctrine (verify-after-the-mutation,
T-0456 intent journal for lands) already treats interrupted mutations as
first-class; the fix engine predates it.

FIX: make `frob check --fix` transactional per run: write planned edits to
a staging area (or per-file .orig snapshots + a journal under .frob/) and
apply atomically at the end -- OR, minimally, write a fix-journal before
the first mutation ("N files pending") and clear it on success, so any
tool/gate can detect and either roll back or loudly refuse on a dirty
abandoned state (same shape as the land intent journal). A kill mid-apply
must leave either the original tree or a detectable, revertable state --
never a silent half-rewrite.
MUST-FIRE: kill the fix engine mid-run (test hook or SIGKILL in a
subprocess fixture) -- the journal detects the abandoned state and
`frob check` refuses/reports it loudly.
MUST-STAY-QUIET: a completed --fix run leaves no journal and no strays.
