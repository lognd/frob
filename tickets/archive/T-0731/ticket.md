---
id: T-0731
title: 'agent file blacklist: version/CHANGELOG/uv.lock/ledger untouchable in worktrees
  -- land owns them exclusively'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/**
- src/frob/scaffold/**
- src/frob/gates/**
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4709: preserve CHANGELOG-exclusion surfacing story trimmed from _docptr.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1109
  new_length: 1722
evidence:
- tests/gates_suite/test_debt.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent
- tests/gates_suite/test_debt.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_uv_lock
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_pyproject_version
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_pyproject_edit_without_version_change_allowed
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_override_env_var_allows_it
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_tickets_md_change_warns_but_does_not_refuse
designated_repro_test: null
acceptance:
- text: GIVEN two concurrent public-API worktrees WHEN both land THEN neither ever
    edited version/changelog files, the land bumps once each, and zero merge conflicts
    occur on those files
  evidence:
  - tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User directive 2026-07-22: eliminate ALL coordinator conflict resolution on version/changelog/ledger files -- measured as the No.1 time sink (every concurrent public-API ticket collided on pyproject/CHANGELOG/uv.lock; three hand-resolved merges in one hour). Mechanism: (1) REL001 suppressed in agent worktrees (FROB_AGENT set, T-0574 env) -- agents never bump; the land step computes the bump, writes pyproject/uv.lock/.frob-release.json, and AUTO-GENERATES the changelog entry from the ticket title/id (changelog becomes derived state, never hand-appended in worktrees); (2) a scaffold-installed guard (pre-commit hook or the T-0574 wrapper pattern) refusing worktree commits touching pyproject version line/CHANGELOG.md/uv.lock unless FROB_LAND_INTERNAL=1; (3) tickets.md stays writable ONLY via the single-writer CLI (already true) -- the guard also refuses raw hand-edits (diff shape without a CLI marker is hard; acceptable v1: hook warns on tickets.md in a commit not created by the frob CLI paths). Playbook updated: agents stop touching version files entirely, delete the bump-and-chase instructions.


T-4709 follow-up (condensed from _ARCHIVAL_LEDGER_FILES's comment block in
src/frob/gates/_docptr.py, trimmed for DOCARCH002's 12-line cap):
the CHANGELOG.md exclusion surfaced concretely as a DOC006 finding on a
symbol that never existed top-level, with no in-worktree path to zero at
all -- the only honest fix would have been editing an immutable record
that T-0731's pre-commit hook correctly refuses to let anyone hand-edit.
Checking release-note prose written in the past against the tree as it
stands today is not this gate's motivating case, and the only way to
satisfy it would be to falsify history.