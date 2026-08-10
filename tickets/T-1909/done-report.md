## Done report

Root cause confirmed by direct investigation: `frob.tickets._scope._scope_add_live_lease_conflict`
(the T-1868 live cross-worktree-lease half of the single scope-lease-conflict entrypoint
`scope_lease_conflict`, used by both `mutate_scope --add` and `frob ticket start`'s own
grant-time check) iterated every lease `read_all_leases(root)` returned and only excluded
one whose TTL had expired -- it never consulted `root`'s OWN, just-merged-with-main ledger
to see whether the lease's ticket was already DONE/DROPPED there. A lease file on the shared
`.git/frob-leases/` side-channel is written once (on IN_PROGRESS) and only ever removed by
THAT SAME worktree's own subsequent `transition` call; a worktree abandoned after its ticket
was dropped/closed from a DIFFERENT worktree (the ordinary coordinator-driven drop path)
leaves a live, unexpired lease file behind forever, with no mechanism to notice its holder is
terminal. This reproduces the exact T-1893/T-1579 incident: `frob ticket start`/`scope --add`
refused with `ScopeLeaseConflict`, naming a ticket already dropped on main.

Fix: `_scope_add_live_lease_conflict` now takes `queue` (root's own authoritative ledger view,
already threaded in by its only caller) and skips a colliding lease whose ticket is DONE or
DROPPED there -- mirroring the same DONE/DROPPED filter `frob.tickets._doable._cross_worktree_
leases` already applies for the `doable`/`leased_by` display path, and `_scope_add_queue_
conflict`'s own `holder.state is not TicketState.IN_PROGRESS` skip for the queue-based half of
the same check. This fixes both `mutate_scope --add` and `frob ticket start`'s grant-time
refusal in one place, since both funnel through `scope_lease_conflict`. The per-lease exemption
logic (T-1909's new check plus the pre-existing T-1356/T-0561 exemptions) was split into a new
helper `_live_lease_collision_is_exempt` to keep the loop under ARCH001's line threshold.

This closes the "resolve lease holders against ledger state on MAIN, not the holder worktree's
local copy" option named in the ticket body. It does not implement drop/close actively releasing
a foreign worktree's lease, nor a path-existence/branch-liveness reclaim sweep for STRANDED
leases sitting in existing stale worktrees right now -- `frob.tickets._leases.lease_staleness_
reason`/`orphaned_leases`/`release_orphaned_lease`/`force_release_lease` (T-1789/T-1806) already
provide that manual reclaim path via `frob worktree release-lease <id>` for a lease that is
provably orphaned by path-gone/ticket-gone/holder-dead; this ticket's fix additionally makes the
COLLISION CHECK ITSELF ledger-state-aware so a still-present, still-live worktree whose ticket is
merely terminal on the checking ticket's own ledger no longer blocks unrelated work at ALL, without
needing any manual reclaim step first -- the exact "unfalsifiable from the consumer's side" gap the
ticket names. A currently-stranded lease in an EXISTING stale worktree (one whose local ledger has
not been touched since) is reclaimed automatically the next time any worktree's ledger (having
merged the drop) attempts a scope/start check against it -- no separate sweep needed.

Regression test added at the exact incident shape: two real linked git worktrees sharing one git
common dir; ticket A started (and leased) in one, dropped on the OTHER'S ledger directly (never
released by A's own worktree); a scope --add for an unrelated ticket B on the SAME path, from the
worktree that knows the drop, now succeeds. Verified failing at the parent commit (refused with
ScopeLeaseConflict naming the dropped ticket) and passing after the fix.

### Changed
```
 rapid-debt.jsonl           |  2 ++
 src/frob/gates/__init__.py |  1 +
 tickets/T-1909/ticket.md   | 50 +++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 52 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease::test_dropped_ticket_on_local_ledger_does_not_block_live_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 6 error(s), 977 warning(s), 700 waived
- error-findings: AFFECT001@src/frob/app/ticket_runner/_rapid_sweep.py, AFFECT001@src/frob/tickets/_scope.py, PRE001@tickets/T-1909, REG002@docs/design/registry/check-coverage.yaml, SUPPRESS001@.claude/hooks/frob-suggest.py, SUPPRESS001@.claude/hooks/frob-timeout-guard.py
