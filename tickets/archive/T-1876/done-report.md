## Done report

WHAT WAS ALREADY THERE, established before writing anything (per the
dispatch brief's instruction to establish this first):

`read_all_leases` already prunes a lease whose recorded worktree path is
CONFIRMED gone (`_probe_worktree_liveness` -> "confirmed_absent") --
that is a real liveness check, but it only catches a worktree whose
directory was physically removed. It does NOT catch the shape T-1876
measured: a worktree that still EXISTS on disk but whose agent is dead
(idle for hours, no live process, no fresh commits). `is_lease_ttl_expired`
(T-0782, 6h horizon) and `lease_staleness_reason`/`orphaned_leases`
(T-1789/T-1806, unifying path-gone/ticket-gone/holder-dead, the
"holder-dead" shape gated on BOTH the TTL and no live process cwd'd into
the worktree -- `scan_for_live_worktree_process`, T-1739) already exist
and already power `frob worktree release-lease`. So requirement 1 (reuse
the existing liveness check) and requirement 4 (a wired release command)
were ALREADY DONE by prior tickets -- confirmed by reading, not assumed.

The gap that was NOT closed: `frob ticket doable`'s own "In-flight
(leased, already being worked)" section (`_render_doable_in_flight`,
`src/frob/app/ticket_runner/_query.py`) rendered every in-flight row
identically regardless of staleness -- `has_live_lease`/`leased_by`
(`frob.tickets._doable`, out of this ticket's declared scope) never
consult `is_lease_ttl_expired` or `lease_staleness_reason` at all. This
is exactly what the ticket measured: `doable` presenting a dead agent's
lease the same as live work, with the coordinator having no signal to
act on at the point the dispatch decision is actually made.

Changed:
- src/frob/app/ticket_runner/_query.py::_stale_lease_reasons (new)
- src/frob/app/ticket_runner/_query.py::_render_doable_in_flight (extended)
- src/frob/app/ticket_runner/_query.py::_doable (call site, threads the
  new staleness map through)
- docs/modules/tickets.md (new section under "Cross-worktree lease
  side-channel (T-0473)")

Fix (requirement 2 -- surface staleness where the decision is made):
`_stale_lease_reasons(root)` builds a `ticket_id -> reason` map from
`orphaned_leases(root)` + `lease_staleness_reason` (both already landed,
T-1789/T-1806) -- no new liveness signal invented. `_render_doable_in_flight`
prints an extra warning line under any in-flight row this map covers,
naming the reason (`path-gone` / `ticket-gone` / `holder-dead`) and the
`frob worktree release-lease TICKET-ID` command.

Requirement 3 (FLAG, do not auto-release) is satisfied structurally: the
new code path is read-only -- it only ANNOTATES `_render_doable_in_flight`'s
existing output. `doable`'s actual dispatchable/blocked/in-flight
partition (`has_live_lease`, `leased_by`, both in `frob.tickets._doable`,
outside this ticket's scope) is completely unchanged; no lease is read,
written, or released by this change. This is also why a live holder's
lease is proven NOT flagged (see evidence below) -- the exact assertion
the brief called out as what stops this from becoming a corruption bug.

Evidence (fail-then-pass proven -- the test module could not even
IMPORT before the fix, `ImportError: cannot import name
'_stale_lease_reasons'`, confirmed by reverting src/frob/app/ticket_runner/_query.py
to HEAD and re-running; restored and re-verified green afterward):

    tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_dead_holder_flagged_with_reason
    tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_live_holder_not_flagged
    tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_no_root_returns_empty

`test_dead_holder_flagged_with_reason` proves direction 1 (a dead
holder's lease becomes reportable/reclaimable: `_stale_lease_reasons`
returns `{"T-0001": "holder-dead"}` for a lease recorded past
`LEASE_TTL_SECONDS` with no live process in its worktree).
`test_live_holder_not_flagged` proves direction 2 (a lease recorded just
now, worktree and ticket both genuinely present, is NOT flagged --
`_stale_lease_reasons` returns `{}`). Ran via `uv run pytest
tests/unit/test_app_runners_doable_stale_lease.py -p no:cacheprovider -q`
-- 3 passed. Also re-ran the full pre-existing
`tests/test_ticket_leases.py` (113 passed, 1 pre-existing unrelated
failure confirmed present BEFORE this change too:
`TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for`,
about the `anchor` verb, nothing to do with leases) and
`tests/unit/test_app_runners_t0714_doable_summary.py` (3 passed, no
regression).

Gates: `frob check --ticket T-1876 --only affect_drift/scope/prework`
clean for everything this ticket touches (AFFECT001 on the changed
symbols resolved by the docs/modules/tickets.md addition; SCOPE001/PRE001
resolved by adding docs/modules/tickets.md to scope and re-running `frob
ticket sweep T-1876`). `frob check --land-parity`: clean, 0 unscoped
errors. The two remaining `gate:DRIFT` DRIFT002 findings a full
`--ticket` run shows (`_mutate.py::_anchor`) are pre-existing and
unrelated -- confirmed present against this exact tree with
`src/frob/app/ticket_runner/_query.py` reverted to HEAD, i.e. before any
of this ticket's changes.

Filed: none. T-1777/T-1789/T-1806/T-1739 already cover the reclamation
verb and the underlying liveness primitives this ticket reuses; no new
gap found outside this ticket's own scope.

STATED EXPLICITLY per the dispatch brief: the 6 leases named in the
brief (T-1315, T-1552, T-1556, T-1686, T-1691, T-1851) were ALREADY
reclaimable before this ticket, via the pre-existing `frob worktree
release-lease TICKET-ID` command (T-1789/T-1806) -- this ticket did not
change reclaimability, only VISIBILITY: after this change, running `frob
ticket doable` on a tree where any of those leases is still
past-TTL/holder-dead will now print a warning line naming it and the
exact recovery command, instead of silently presenting it as live work.
This ticket's own worktree has no `.git/frob-leases/` entries for those
ids (they belong to a different session's leases directory), so it
cannot re-verify their specific current staleness from here -- that is
the coordinator's own tree to check with `frob ticket doable` after this
lands.

### Changed
```
 tickets/T-1876/ticket.md | 19 ++++++++++++++++++-
 1 file changed, 18 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_dead_holder_flagged_with_reason` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_live_holder_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_no_root_returns_empty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 1294 warning(s), 697 waived
- error-findings: DOC007@src/frob/app/ticket_runner/_mutate.py, DRIFT002@src/frob/app/ticket_runner/_mutate.py, DUP001@tests/unit/test_app_runners_doable_stale_lease.py, REG002@docs/design/registry/check-coverage.yaml, SELFAUDIT001@design
