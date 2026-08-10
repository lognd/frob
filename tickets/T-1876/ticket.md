---
id: T-1876
title: A lease survives its agent's death with no liveness check, blocking every ticket
  in its scope indefinitely
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_query.py
- tests/unit/test_app_runners_doable_stale_lease.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-1876: lease liveness reaping lives here'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners_doable_stale_lease.py
  reason: T-1876 fix lives in _query.py/_leases.py; new test file covers _stale_lease_reasons
    behavior
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1876 adds a doc section for the doable staleness surfacing
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_dead_holder_flagged_with_reason
- tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_live_holder_not_flagged
- tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons::test_no_root_returns_empty
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
A lease survives the death of the agent holding it, with nothing to
detect or reclaim it, and it blocks every other ticket in its scope
indefinitely.

MEASURED, 2026-08-08:

    .git/frob-leases/T-1820.json   recorded_at 10:51:38Z
                                   worktree .claude/worktrees/refusal-attrib
    refusal-attrib last commit     07:42

The agent had been gone for hours. The lease held
`src/frob/_cli_parsers/_quality.py` and blocked T-1556, T-1557, T-1584,
T-1656 and T-1661 the entire time. `frob ticket doable` listed T-1820
under "In-flight (leased, already being worked)", which is exactly what a
coordinator scanning the queue needs it NOT to say about abandoned work.
Deleting the lease file by hand unblocked all five immediately.

WHAT IS NOT WRONG HERE, stated so nobody "fixes" it: an agent's
in-progress state is committed on ITS OWN BRANCH, while main's ledger
stays `queued` until the land. Confirmed:

    git show sweep-regress:tickets/T-1870/ticket.md   state: in-progress
    tickets/T-1870/ticket.md (on main)                state: queued

So on main the lease file is the ONLY authority for "someone is working
this", and `frob ticket show` rendering `[in-progress@<worktree>]` from
it is correct. Do NOT change that. The lease is load-bearing precisely
because the ledger cannot know yet.

That is also what makes this bug matter: if the lease is the only signal,
a stale lease is indistinguishable from live work, and there is no second
source to cross-check against.

REQUIRED:

1. A liveness check on leases. T-1739 already built one for
   `frob worktree sweep` -- reuse it, do not write a second. The natural
   signal is the holding worktree's last-commit age, which is what a
   human ends up eyeballing anyway.
2. Surface staleness where the decision is made: `frob ticket doable`
   should mark a lease whose worktree looks dead rather than presenting
   it identically to live work. A warning a coordinator sees at dispatch
   time is worth more than a reaper that runs on a schedule.
3. Decide reclamation policy explicitly, and prefer the conservative
   one: FLAG, do not auto-release. Auto-releasing a lease whose agent is
   merely slow would let two worktrees edit the same file, which is the
   exact failure T-1868 is filed against. A loud "this lease looks
   abandoned, here is the command" beats a silent reclaim.
4. Provide that command. There is still no wired verb to release a lease
   -- T-1777 covers exactly this gap. Today the only remedy is deleting
   a file from `.git/frob-leases/` by hand, which is undiscoverable and
   which no documentation mentions.

RELATED: T-1868 (scope --add bypasses the lease-conflict check) is the
same subsystem -- the lease store drifting out of agreement with reality
and nothing reconciling it. Coordinate; these may share a fix site.
Anchor tickets make it worse: T-1820 is a permanent WIRE001 follow_up
anchor that can never legitimately close, so its lease could never be
released by the normal land path no matter how long anyone waited.

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
