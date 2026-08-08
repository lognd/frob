## Done report

Unified the three orphaned-lease shapes into one predicate,
`lease_staleness_reason(root, record) -> str | None`
(`src/frob/tickets/_leases.py`): `"path-gone"` (T-1789's original
check), `"ticket-gone"` (the recorded ticket id is absent from `root`'s
authoritative ledger -- the exact shape that hard-deadlocked the
incident this ticket documents, since `frob ticket drop` cannot find
the ticket to drop it), and `"holder-dead"` (worktree and ticket both
exist, the lease has passed `is_lease_ttl_expired`'s horizon, AND no
live process is cwd'd into the worktree -- gated on TTL, not the
process scan alone, because a dispatched agent's worktree has no
persistent process sitting in it between tool calls; an ungated check
would misjudge every actively-worked ticket as stale).

`orphaned_leases` and `release_orphaned_lease` (both pre-existing,
T-1789) now build on this single predicate instead of `orphaned_leases`'
own `Path(...).exists()`-only check, so both cover all three shapes with
no divergence between "report" and "release" logic. `frob worktree
release-lease TICKET-ID`'s CLI messaging (`src/frob/app/
worktree_runner.py`) updated to match the generalized "not stale"
refusal wording.

Regression-tested the exact hard-deadlock the coordinator's fresh
incident named: `TestReleaseOrphanedLease.test_releases_a_ticket_gone_lease`
first asserts `frob ticket drop` on the ticket-gone id fails (SystemExit,
lease file untouched), THEN asserts `release_orphaned_lease` clears it --
demonstrating the CLI-drop path is a genuine dead end and the new
predicate is the only resolution.

`scan_for_live_worktree_process` (pre-existing, T-1715/T-1739) already
avoids the `pgrep -f` self-match trap flagged by the coordinator -- it
walks `/proc` directly, explicitly excludes `os.getpid()`, and matches
on `/proc/<pid>/cwd` resolution, never a command-line substring.

Merged main before landing (2 commits behind: T-1479/T-1508 daemon-proxy
work). Reset `pyproject.toml`/`uv.lock` to main's version per the
coordinator's note (neither is in this ticket's scope).

### Changed
```
 design/frob.strata              |  35 ++++----
 src/frob/app/worktree_runner.py |  16 ++--
 src/frob/tickets/_leases.py     | 148 ++++++++++++++++++++++++-------
 tests/test_ticket_leases.py     | 192 ++++++++++++++++++++++++++++++++++++++--
 tickets/T-1806/ticket.md        |  25 +++++-
 5 files changed, 354 insertions(+), 62 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 760 warning(s), 735 waived
- error-findings: none (measured, zero errors)
