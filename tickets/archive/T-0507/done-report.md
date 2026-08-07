## Done report

Extended the T-0431 FROB_WORKTREE lease guard (enforce_worktree_lease) to
the two remaining mutating entry points named in the ticket:

1. frob.release.stamp (src/frob/release/__init__.py) -- the function that
   writes .frob-release.json. Added ReleaseError.WorktreeLeaseViolation and
   a guard check at the top of stamp(), same shape as gates._baseline's
   stamp_baseline/stamp_coverage (T-0431).
2. frob.app.ack_runner.run (src/frob/app/ack_runner.py) -- the CLI entry
   point that writes frob.lock. Added the guard check directly at the top
   of run() (exit 1 + logged error on violation), since frob.graph.lock is
   out of this ticket's declared scope (src/frob/release/, src/frob/app/
   only) and the CLI layer is where every other T-0431 guard call site
   already lives for commands whose core module sits outside scope.

Both follow the exact T-0431 contract: FROB_WORKTREE unset is a no-op
(unrestricted); set-and-mismatched refuses loudly; set-and-matching
proceeds normally.

New tests (tests/test_release_worktree_lease.py,
tests/test_ack_worktree_lease.py) mirror tests/test_gates_worktree_lease.py's
style: a real git repo in tmp_path, FROB_WORKTREE set/unset/mismatched via
monkeypatch, asserting Err(WorktreeLeaseViolation)/exit vs normal-path
behavior.

Scope was widened (frob ticket scope) to add the two new test files, plus
tickets-archive.md -- the latter purely because T-0519 (worked earlier in
this same sequential worktree) already committed a tickets-archive.md
change that still shows in the diff-vs-main SCOPE001 check, the same
"sequential single-worktree dispatch" precedent T-0431's own scope_changes
documents for T-0357/T-0338/T-0409.

frob release check reports "none change -> need >= 0.52.0 (current
0.52.0): OK" -- adding one ErrorSet member did not trip the bump
requirement, so no REL001/version bump was needed this ticket.

Gates: uv run frob check --ticket T-0507 --json -> 0 new errors from this
ticket's changes; remaining errors (gate:DOC DOC003 on docs/commands/sys.md,
gate:REG REG003 x5 on docs/design/registry/weaknesses.yaml) are pre-existing
repo-wide debt, unrelated to src/frob/release/ or src/frob/app/ack_runner.py
(verified identical error set present before this ticket's scope was even
touched, see T-0519's Done report which observed the same DOC/REG errors).

### Changed
```
 src/frob/app/ack_runner.py           |  14 +++-
 src/frob/release/__init__.py         |  14 +++-
 tests/test_ack_worktree_lease.py     |  55 +++++++++++++++
 tests/test_release_worktree_lease.py |  52 ++++++++++++++
 tickets-archive.md                   |  17 ++---
 tickets.md                           | 129 +++++++++++++++++++++++++++++++++--
 6 files changed, 260 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_release_worktree_lease.py::TestStampWorktreeLease::test_mismatched_lease_refuses` (pytest node id, verified passing when recorded)
- `tests/test_release_worktree_lease.py::TestStampWorktreeLease::test_no_lease_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ack_worktree_lease.py::TestAckWorktreeLease::test_mismatched_lease_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ack_worktree_lease.py::TestAckWorktreeLease::test_no_lease_reaches_normal_ack_failure` (pytest node id, verified passing when recorded)
