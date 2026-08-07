## Done report

Implemented both halves of T-0479 in `src/frob/tickets/_land.py`:

(a) Added `_splice_only_ticket(main_text, worktree_text, ticket_id, ...)`,
a ledger splice that takes MAIN's ledger as the base and overlays ONLY the
landing ticket's own block from the worktree; every sibling ticket id comes
from main untouched. This is the structural fix for the T-0475 incident
(landing one ticket resurrected a stale in-progress state for unrelated
sibling tickets that had since been requeued back to queued on main): the
old `splice_ledger` merged the WHOLE ledger by id, so a worktree's stale
copy of a sibling ticket could out-rank main's newer (but lower-ranked,
because requeue moves backward through the state machine) state.
`_splice_and_stage` grew an optional `ticket_id` parameter that switches it
to the scoped splice; both of `land()`'s ledger-writing sites --
`_merge_main_into_worktree` (merging main into the worktree) and
`_squash_and_splice_ledger` (the final squash-apply onto main) -- now pass
the landing ticket's id, so both directions of the splice are scoped, not
just the last one. `splice_ledger` itself is unchanged and still used
verbatim elsewhere (e.g. the `frob ticket merge-driver`, and the two
existing `TestSpliceLedger`/`test_ticket_merge_driver.py` suites), since
the true multi-ticket merge is still the right operation there.

(b) Added `_auto_resolve_out_of_scope_conflicts(cwd, ticket, keep=...)`:
after a merge/squash step leaves some paths conflicted, every conflicted
path OUTSIDE `ticket.scope` (via the existing `scope_matches`) is resolved
by `git checkout --<keep>` (`ours`/`theirs`, whichever side is "main" for
that merge direction) + `git add`, since the worktree never legitimately
touched a file it wasn't scoped to change -- a conflict there is
definitionally unrelated noise, not an editorial decision. Only conflicts
that remain (in-scope files, or an out-of-scope checkout that itself
failed) are still surfaced as `MergeConflict`/`SquashConflict` for manual
resolution. `_check_only_tickets_conflicted` and `_check_squash_conflicted`
(the latter's signature changed from `final_id: str` to `ticket: Ticket`,
since scope-matching needs the ticket, not just its id) were rewritten on
top of this shared helper. `tickets.md` is still excluded unconditionally
from checkout-based resolution -- it is always resolved via the ledger
splice, never `git checkout`.

Also hand-edited T-0475's frontmatter `state: queued` -> `state: dropped`
per this ticket's "Subsumes T-0475" clause (the precedented drop mechanism
for a superseded ticket) -- T-0479's fix subsumes what T-0475 asked for.

Ran `uv run ruff format`/`uv run ruff check` on only the two files this
ticket touched (a pre-existing, out-of-scope E501 in
`src/frob/strata/_scenarios.py` was left untouched).

CAVEAT: `frob check --ticket T-0479` still reports the repo's pre-existing
gate backlog (waived findings across `frob-dup`/`frob-arch`/etc. unrelated
to this ticket's files) -- none of it newly introduced by this change; see
the scoped `uv run ruff check`/`pytest` runs above for what this ticket's
own files actually gate clean on.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestSpliceOnlyTicket::test_sibling_state_never_taken_from_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceOnlyTicket::test_landed_tickets_own_divergence_still_resolved` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestOutOfScopeConflictAutoResolved::test_conflict_outside_scope_takes_mains_side_and_lands` (pytest node id, verified passing when recorded)
