## Done report

THE TWO DISAGREEING CODE PATHS (both in scripts/fleet_status.py, both
named as required):

1. `worktrees()` (scripts/fleet_status.py:480, the WORKTREES section's
   own gather function) unconditionally lists every directory under
   `WORKTREES` with `WORKTREES.iterdir()` -- no ticket correlation at
   all, no lease check, nothing. Any directory that exists appears.

2. `_resolve_worktree_for_in_progress_ticket` (scripts/fleet_status.py:
   422, the LEASES section's own worktree-resolution half of
   `in_progress_ticket_scope_leases`) tries the recorded lease file
   first, then (before this fix) fell straight through to
   `worktrees_touching_ticket` (scripts/fleet_status.py:1239), which
   requires an UNLANDED commit that touches the ticket's own declared
   SCOPE files. A worktree that has done nothing yet but `frob ticket
   start`/`work` (one commit: the start-transition ledger commit) has
   no such commit and was reported LEAKED, even though it is genuinely
   live and even though `worktrees()` lists the exact same directory in
   the SAME report -- confirmed live: T-3394 was `in-progress` with a
   real worktree, WORKTREES listed it with a 7-minute-old commit
   (its start-transition commit), LEASES reported `[LEAK]`.

Root cause was NOT the suspected path-shape mismatch -- checked (per
the ticket's own instruction not to assume): `record_lease` always
writes an absolute, `.resolve()`d path
(src/frob/tickets/_leases.py:686), and `_resolve_worktree_for_in_
progress_ticket`'s `Path(recorded).is_dir()` check works correctly
against an absolute path regardless of fleet_status.py's own cwd. The
real defect was that `worktrees_touching_ticket`'s scope-correlation
scan answers a DIFFERENT, stricter question ("has this ticket been
IMPLEMENTED", built to rule out misattribution across candidate
worktrees, T-2114/T-2181) than the one `_resolve_worktree_for_in_
progress_ticket` actually needs ("which worktree is holding this
LEASE"), for which "has this worktree structurally STARTED the ticket"
(`_worktree_started_ticket`'s start-transition-commit signal, already
used elsewhere in this same file, T-2747) is sufficient and matches
what `worktrees()` itself effectively assumes.

FIX: unified the two paths by adding a step in `_resolve_worktree_for_
in_progress_ticket`, between the lease-file check and the scope-
correlation fallback -- scan WORKTREES directly for any directory
whose history carries `ticket_id`'s start-transition commit
(`_worktree_started_ticket`) and return it immediately if found. The
scope-correlation fallback (`worktrees_touching_ticket`) still runs
after it, unchanged, for the T-3128 case (a start-transition commit
that already landed via a sibling ticket's squash and so no longer
appears in `main..HEAD`).

Reproduced with a REAL git worktree (not a string/JSON fixture,
`TestInProgressTicketScopeLeasesLiveGit`'s own established pattern):
a real `git worktree add`, one commit (`--allow-empty`, the exact
start-transition commit shape `frob ticket start` writes), no scope-
touching commit, no lease file. Must-fire test genuinely fails against
the unfixed detector (FAILED_AT_PARENT, verified via `frob ticket
evidence --check-repro --base-ref` against the test-committed-alone
parent). Must-stay-quiet: both pre-existing regression controls in the
same class re-run green -- a genuinely-absent worktree is still LEAKED
(`test_no_worktree_and_no_lease_is_still_leaked`), and the scope-
correlated fallback still resolves a worktree whose lease file was
removed but which HAS made a real scope-touching commit
(`test_live_worktree_with_lease_file_removed_is_not_leaked`).

Scope note: T-3403's own filed scope globs (scripts/fleet_status.py,
tests/unit/test_fleet_status*.py, docs/guides/coordinator-scripts.md)
were correct; only their RECORDED REASONS were mis-paired due to T-3404's
now-fixed --reason-collapse bug (the coordinator's own observation).
Left untouched per the audit-trail-is-append-only rule -- not
retroactively corrected.

### Changed
```
 scripts/fleet_status.py                | 46 +++++++++++++++++---
 tests/unit/test_coordinator_scripts.py | 78 ++++++++++++++++++++++++++++++++++
 tickets/T-3403/ticket.md               |  6 ++-
 3 files changed, 122 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_freshly_started_worktree_with_no_scope_commit_yet_is_not_leaked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_no_worktree_and_no_lease_is_still_leaked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 19 error(s), 4219 warning(s), 857 waived
- error-findings: AFFECT001@scripts/fleet_status.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC006@tickets/T-3410/ticket.md, DOC006@tickets/T-3411/ticket.md, DOC011@docs/modules/tickets.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3403, REL001@src/frob/__init__.py, SELFAUDIT001@design, SYS003@src/frob/gates/__init__.py, SYS003@src/frob/tickets/_scope_coverage.py, SYS003@tests/unit/test_nodeid.py, TEST001@src/frob/lang/__init__.py, TEST001@src/frob/lang/_extract.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/nodeid.py
