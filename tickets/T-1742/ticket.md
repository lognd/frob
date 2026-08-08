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

## Done report

Fixed the pre-commit land-owned-file guard (`_FORBID_LAND_OWNED_FILES_SCRIPT`
in `src/frob/scaffold/project.py`) so it no longer refuses a legitimate
`git merge main` merge commit that carries forward main's own
land-generated changes to CHANGELOG.md/uv.lock/pyproject.toml's version
line.

Chose the second of the ticket's two suggested fixes: compare the staged
blob for each land-owned file against `main`'s current tip
(`_t1742_staged_diverges_from_main`, added inline in the hook script) and
refuse only when they actually differ. A merge commit whose resolved
content is byte-identical to main's tip (the routine forward-merge case)
is no longer refused; a genuine hand-edit -- including one smuggled in
via a merge's own conflict resolution -- is still refused exactly as
before. If `main` cannot be resolved at all, the check fails safe
(treats the file as diverging), so the guard never goes silently inert.

Scope was narrowed to `src/frob/scaffold/_managed.py` only at ticket
creation, but the actual guard script this ticket's fix targets lives in
`src/frob/scaffold/project.py` (`_managed.py` only imports and reuses it
via `_expected_hook_body`) -- extended scope to include
`src/frob/scaffold/project.py`, its test file
`tests/test_scaffold_worktree_lease_hook.py`, and
`tests/unit/test_scaffold_managed.py` before starting real work, per
`frob ticket scope --add` with reasons recorded in the scope_changes
audit trail. Also added `tickets/T-1742/**` after `SCOPE001` flagged the
ticket's own per-ticket ledger file, written by ordinary `frob ticket`
CLI lifecycle commands (start/scope/evidence/sweep).

Two new tests added to `tests/test_scaffold_worktree_lease_hook.py`:
one confirms a merge commit reproducing main's CHANGELOG.md content
byte-for-byte is allowed; the other confirms a merge commit whose
conflict resolution introduces a hand-edited CHANGELOG.md is still
refused. All 8 pre-existing tests in that file continue to pass
unmodified -- the guard's real-hazard behavior (a plain hand-edit commit,
no merge in progress) is unweakened.

### Changed
```
 src/frob/scaffold/project.py               |  46 ++++++++++--
 tests/test_scaffold_worktree_lease_hook.py | 111 +++++++++++++++++++++++++++++
 tickets/T-1742/ticket.md                   |  35 ++++++++-
 3 files changed, 184 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_merge_commit_matching_main_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_merge_commit_diverging_from_main_still_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 584 warning(s), 732 waived
- error-findings: none (measured, zero errors)
