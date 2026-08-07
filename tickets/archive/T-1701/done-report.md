## Done report

Folded T-1707 (my own independently-filed duplicate of this ticket,
found while landing T-1683) into this one via `frob ticket drop
T-1707 --absorbed-by T-1701`. T-1707's investigation was more precise
than this ticket's own original body about WHERE the bug lives:
`_finalize_and_close_ticket` in `src/frob/tickets/_land_finalize.py`
(not `_validate_closeable` as originally guessed) is what unconditionally
forces a `dropped -> done` transition and is the direct cause of the
`InvalidTransition`/`CloseFailed` an agent hits landing a dropped ticket.
`_validate_closeable` (`src/frob/tickets/_land_merge.py`) turned out to
be a SECOND, independent gap: it unconditionally requires evidence + a
Done report regardless of ticket state, which is also wrong for DROPPED
but is a PRE-merge check (fires before `_close_finalized_ticket` is ever
reached) -- both had to be fixed for a dropped ticket to land end to end.

FIX.

1. `_has_drop_reason` (new, `_land_merge.py`) -- the DROPPED-side twin
   of the existing `_has_done_report`: a `## Drop reason` heading with
   at least one real (non-blank) line under it. `drop_ticket` already
   refuses an empty reason at write time (`DropReasonMissing`), so this
   is a trustworthy signal, not a new requirement invented here.

2. `_validate_closeable` now branches on `ticket.state ==
   TicketState.DROPPED` FIRST: requires only `_has_drop_reason`, skips
   evidence/Done-report/acceptance-binding entirely (none of those are
   applicable to a ticket explicitly cut, not done).

3. `_skip_close_for_legitimate_drop` (new, `_land_finalize.py`, split
   out of `_close_finalized_ticket` to keep it under ARCH001's line
   threshold) -- if the ticket is DROPPED in the worktree AND carries a
   real drop reason, returns `Ok(final_id)` immediately, mirroring the
   existing "already DONE" retry-idempotency early-return right above
   it, so the caller proceeds straight to squash-apply instead of
   attempting an illegal `dropped -> done` transition.

   Deliberately gated on `_has_drop_reason`, not bare `state ==
   DROPPED`: `tests/test_ticket_land.py::TestCloseFailAfterMerge::
   test_close_fails_after_merge_when_main_dropped_same_id` (pre-existing,
   unmodified) exercises a genuine RACE this must not paper over -- main
   independently ends up DROPPED for the same ticket id via an unrelated
   write with no reason recorded, the ledger splice's state-rank
   preference adopts that DROPPED state post-merge even though the
   worktree was legitimately landing a DONE ticket, and that case must
   keep refusing loudly (`InvalidTransition` -> `CloseFailed`, the
   fall-through this change preserves) rather than silently publishing
   an unintended drop. Confirmed by running the existing test: it
   initially broke under a state-only check, is green again with the
   reason-gated one.

Requirement 3 (DROPPED visible in `board`/epic progress, not folded into
"done") verified already satisfied by construction, no change needed:
`board_view` (`frob.tickets.__init__`) groups strictly by `t.state is
state` over `BOARD_STATES`, and `TicketState.DROPPED`/`TicketState.DONE`
are already distinct enum values with their own board columns.

Requirement 4 (T-1675 coordination): not touched. T-1675's own "no code
changed" vs "docs-only ticket" ambiguity in the ALREADY-LANDED preflight
(`_ledger_ticket_at_ref`/`on_main.state is not TicketState.DONE`,
`_land.py`) is orthogonal to this fix -- a not-yet-landed DROPPED ticket
cannot have `state=done` on `base_ref` (only close/land ever write that),
so T-1675's own positive signal never fires for the DROPPED case this
ticket adds. Left as-is per "coordinate, do not duplicate."

Two full end-to-end regression tests (`tests/test_ticket_land.py::
TestLandDroppedTicket`), both driving the real `land()` entry point
through a real worktree/git-fixture (`repo` fixture), matching the
ticket's own suggested acceptance criteria exactly:
- a queued ticket transitioned in-progress, then dropped with a real
  reason via `drop_ticket`, lands cleanly; the ticket's final state on
  main is DROPPED and its body carries the recorded reason.
- the same shape but hand-transitioned to DROPPED with `transition()`
  directly (bypassing `drop_ticket`, so no `## Drop reason` section
  exists -- only reachable by hand-editing the ledger, `frob ticket
  drop` itself always refuses an empty reason) refuses with
  `LandError.NotCloseable`.
Both verified to fail without the fix (reverted both changed functions
locally, re-ran, restored) -- and the full existing `tests/test_ticket_
land.py` suite (235 tests) still passes unmodified, including the race
test above.

A pre-existing type-annotation bug in `tests/unit/test_ticket_runner_
gate_findings.py` (T-1703's own fixture helper, `list[...]`-annotated
parameter given a tuple default) surfaced by `frob check --land-parity`
while verifying this ticket's own changes; fixed inline (scope extended
with --reason) rather than left on main or spun into separate process
overhead for a 2-line type fix.

Verified via `frob check --land-parity` that every remaining unscoped
error is genuinely pre-existing and unrelated to this ticket's diff (`git
diff main --stat` confirms none of `src/frob/tickets/_evidence.py`,
`docs/audits/docs-completeness-2026-08-06.md`,
`src/frob/gates/_markdown_scan.py`,
`tests/unit/gates/test_markdown_scan.py`, or
`tests/test_ticket_work_and_land_finish.py` are touched by this change;
the `tickets.md` TICK006 finding names T-1700, a different ticket).

### Changed
```
 tickets.md | 8 +++++---
 1 file changed, 5 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 756 warning(s), 715 waived
- error-findings: ARCH001@src/frob/tickets/_evidence.py, DOC009@docs/audits/docs-completeness-2026-08-06.md, INV006@src/frob/gates/_markdown_scan.py, PII012@tests/unit/gates/test_markdown_scan.py, TICK006@tickets.md, unresolved-attribute@tests/test_ticket_work_and_land_finish.py
