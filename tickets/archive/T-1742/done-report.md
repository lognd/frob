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
