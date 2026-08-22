## Done report

### Acceptance 1/2: the suspected mechanism does NOT reproduce

Reproduced the exact real sequence T-2259's git history showed (a `scope
--add` while the ticket is still QUEUED -- before `_auto_plan_if_queued`'s
own queued->planned write -- immediately followed by the planned->
in-progress transition, from a real linked `git worktree`, visible from a
SECOND worktree via the shared `.git/frob-leases/` side channel) twice:
once ad hoc against a throwaway git repo via the real `frob` CLI (`frob
ticket scope T-0001 --add ... ; frob ticket start T-0001`, both single-shot
and repeated 4x to match T-2259's own 4 `scope` commits), and once as a
proper pytest regression
(`TestCrossWorktreeLeaseVisibility.test_scope_change_while_queued_then_start_leases_with_post_change_scope`).
Both ways: the lease is recorded correctly, with the POST-change scope,
every time. `mutate_scope` correctly does NOT record a lease for a
not-yet-in-progress ticket (nothing to lease yet); the subsequent
IN_PROGRESS transition's own `_sync_cross_worktree_lease` call records it
with whatever scope is on disk AT THAT MOMENT (freshly reloaded inside
`transition`, never a stale pre-change snapshot). `_evidence.py` has no
defect here.

### Acceptance 4: the actual mechanism (not "it works now")

`frob ticket land`'s own `_land_finalize_and_close`
(`src/frob/tickets/_land_finalize.py`) calls `_finalize_and_close_ticket`,
which transitions the ticket to DONE **in the WORKTREE**, well BEFORE
`_land_squash_apply` (land's own docstring: "the ONLY step that mutates
root") propagates that state to the primary checkout's copy of
`tickets/<id>/ticket.md`. `_sync_cross_worktree_lease`'s `from_state is
TicketState.IN_PROGRESS` branch releases the shared lease SYNCHRONOUSLY
and unconditionally the instant that local transition runs -- correct,
intentional behavior (T-0473's whole point: the lease answers "is anyone
actively holding this right now", worktree-local and immediate).

The result: for the entire window between a land's local close and its
squash-apply reaching root -- which can be minutes under a real gate-check
pipeline -- a ticket reads `state: in-progress` from `main` while holding
NO shared lease at all. This is exactly T-2259's observed shape (`state:
in-progress` on main, no `.git/frob-leases/T-2259.json`, confirmed across
three observations including "while its land was in flight") and needs no
scope-change involvement to explain: T-2259's own git history shows its
land landed as the VERY NEXT commit after its start transition, so its
land was almost certainly already running (past its own local close) for
most or all of the ~20-minute observation window the coordinator measured.

Reproduced directly, independent of `_land.py` entirely, via
`test_local_close_releases_the_lease_before_a_second_worktree_sees_done`:
a ticket transitioned IN_PROGRESS -> DONE in one worktree loses its shared
lease immediately, even though a SECOND worktree's own local ledger view
(standing in for the primary checkout before a land's squash-apply reaches
it) has never even heard of the ticket yet. The lease and a peer's stale
ledger read answer different questions, by design -- this is not the
scope-change-then-start ordering interaction the ticket suspected, and it
is not a lease-recording bug at all.

### Acceptance 3 (MUST-STILL-PASS)

Unaffected -- no production code changed. `tests/test_ticket_leases_cross_worktree.py`
and `tests/test_ticket_leases.py` (160 tests) green, including the
existing ordinary-start, transition-out-releases, and terminal-ticket
tests this ticket's own constraints named.

### What this means for the fix

There is no defect in `_evidence.py`/`_sync_cross_worktree_lease` to fix
-- both the ordinary case and the suspected scope-change case round-trip
correctly, proven by real regression tests, not assertion. The narrower,
real gap is that T-2225's `scripts/fleet_status.py` scope-collision check
reads leases only, so it is blind to a ticket whose land is actively
running (files still genuinely contended until the merge is durable).
Filed as **T-2281** (`scripts/fleet_status.py`, out of this ticket's own
declared scope) rather than fixed here: the fix is a THIRD signal
(`_land_in_progress_for_ticket`, already built for T-2264's identical
class of problem), not inferring occupancy from ticket state -- this
ticket's own explicit "do not" constraint stays honored.

### Changed
```
tests/test_ticket_leases_cross_worktree.py | +2 tests
```

### Filed
T-2281 (`scripts/fleet_status.py` land-in-flight collision-check gap).
