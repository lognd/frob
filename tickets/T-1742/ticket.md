---
id: T-1742
title: pre-commit land-owned-file guard refuses legitimate git merge main commits
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_managed.py
- src/frob/scaffold/project.py
- tests/test_scaffold_worktree_lease_hook.py
- tests/unit/test_scaffold_managed.py
- tickets/T-1742/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/project.py
  reason: the land-owned-file guard script (_FORBID_LAND_OWNED_FILES_SCRIPT) that
    needs the merge-commit exemption is defined in project.py, not _managed.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: test coverage for the pre-commit hook script and _managed.py status functions
    being modified
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_scaffold_managed.py
  reason: test coverage for the pre-commit hook script and _managed.py status functions
    being modified
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1742/**
  reason: ticket's own per-ticket ledger file (tickets/T-1742/ticket.md) is written
    by the frob ticket CLI as part of ordinary ticket lifecycle commands (start/scope/evidence/sweep)
    and SCOPE001 flags it as out-of-scope otherwise
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_merge_commit_matching_main_is_allowed
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_merge_commit_diverging_from_main_still_refused
designated_repro_test: null
threat: null
component: null
---
The scaffolded `.git/hooks/pre-commit` (T-0431/T-0731's land-owned-file
guard) has no exemption for an ordinary `git merge main` merge commit --
it refuses ANY commit whose staged file list contains CHANGELOG.md,
uv.lock, or a pyproject.toml version-line diff, with no check for
whether MERGE_HEAD exists or whether the staged content is byte-
identical to main's own copy (the common case: a worktree merging main
forward legitimately carries main's own land-generated changes to these
files, with zero local divergence).

Hit directly today: `git merge main` in a long-lived worktree pulled
forward several of main's own lands (each of which legitimately bumped
CHANGELOG.md/pyproject.toml/uv.lock), and the resulting merge commit
was refused outright by the hook, even though `git diff main -- \
CHANGELOG.md pyproject.toml uv.lock` was empty (the merged content
exactly matched main -- no hand-edit, no divergence, nothing for the
guard to actually be protecting against). Worked around this once with
`FROB_LAND_INTERNAL=1` for that single commit after verifying byte-
identity to main first; the playbook explicitly says this env var
should never be set by a worktree agent, so this was a one-off, not a
repeatable answer.

Fix: exempt the guard when `$(git rev-parse -q --verify MERGE_HEAD)`
succeeds (a real merge commit in progress), or narrow it further to
only refuse when the staged content of the land-owned file actually
DIFFERS from main's current tip (a hand-edit, not a merge fast-
forwarding main's own history). Either fix removes the false refusal
without weakening the guard against the real hazard (T-0731: a
worktree agent hand-editing these files itself).