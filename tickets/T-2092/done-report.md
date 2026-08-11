## Done report

renumber_one_v2 (the live v2-mode `renumber_one` backend, matching this
repo's default per T-1553) validated its target id was free UNLOCKED, then
persisted under only `ticket_lock` -- a completely different lock file from
`new_ticket`'s own `ledger_lock`. The two paths shared no lock at all, so
`new_ticket`'s own unconditional `atomic_write` (no existence check) could
silently clobber a just-renumbered ticket's content when both raced onto the
same id, with BOTH calls reporting `Ok`. Confirmed by direct probe before
writing any test, then reproduced as a real pytest failure
(TestRenumberVsNewTicketAllocationRace, designated repro, FAILED_AT_PARENT
at e9213a0ca).

Fix: `allocator_lock` (T-1253, the lock T-1669 already wired into
`finalize_draft`/`finalize_draft_for_land`) now wraps the validate-through-
persist span of `renumber_one_v2`, `renumber_one`'s v1 branch, and
`new_ticket`'s own `_allocate_and_write_new_ticket` -- all three id-
allocating call paths now share one lock, so a concurrent renumber and
new_ticket always serialize and whichever runs second re-validates against
the fresh post-write state.

Half 2 (detecting a duplicate id AFTER a merge silently resolves it, the
actual cross-worktree mechanism of the T-2083/T-2090 field incident) is
separate engineering scope -- filed as a follow-up ticket per this ticket's
own instructions, with today's session evidence cited. acceptance[1]/[2]
removed via `frob ticket accept --remove` with that reasoning recorded.

Filed: T-2105

## Two further occurrences, reported by the coordinator mid-session (2026-08-10)

Occurrence 3: main and worktree t-2089 simultaneously held DIFFERENT ticket
bodies at id T-2091 ("LAND-PROOF prints verified=True for lands whose claims
re-verification was skipped as unmeasured" on main vs. "TestRevalidateDispatchableSweepTickets:
two tests intermittently interfere when run together" in t-2089). Caught by
a human diffing the two copies before land; a merge would have silently
destroyed one, same shape as the original T-2090 incident this ticket
reproduces.

Occurrence 4 is the one that matters most for this fix's design: after
occurrence 3, the coordinator instructed the next agent to VERIFY an id was
free before renumbering. It did -- checked T-2096, found it free, took it.
T-2079's agent independently ran the identical check at nearly the same
moment, got the identical answer, and also took T-2096, landing first. Both
agents followed correct, diligent procedure and still collided. This is
direct field confirmation that "verify then claim" cannot be made safe by
discipline alone -- the window between check and commit is exactly what a
lock closes and nothing else can. Recorded as an explicit DO-NOT acceptance
criterion (acceptance[1]) so this ticket cannot be closed by a documentation
or checklist remedy.

Both occurrences were caught by a HUMAN manually diffing two copies --
nothing in the tooling flagged either one. That is exactly the gap
T-2101 (half 2, detection) exists to close; it is not being
deferred quietly.

## Occurrences 5-7, one landing sequence, escalated by the coordinator (2026-08-10)

A single agent landing ONE ticket had to renumber its own follow-up id FOUR
times, colliding three more times in the process, on top of the four
occurrences already recorded above (seven total in one day):

    T-2091 -> collided (the coordinator's own LAND-PROOF ticket)
    T-2096 -> collided (T-2079's citation-rewrite follow-up)
    T-2098 -> collided (the coordinator's own `make -n` ticket)
    T-2100 -> finally landed

The agent re-verified immediately before landing, as instructed, and still
collided twice more -- further field confirmation, independent of
occurrence 4, that the window between "check free" and "claim" cannot be
closed by checking harder or by re-checking closer to the write. The
coordinator also noted its own filing load (T-2094 through T-2099 filed in
rapid succession while agents were landing) is normal, intended concurrent
load, not a misuse to be worked around by "file fewer tickets" or "stagger
filings" -- the fix has to make that load safe, not ask for less of it.

## Occurrence 8: this ticket's OWN half-2 follow-up collided, blocking THIS fix's own land

After close, `frob ticket land T-2092` refused with `CrossTicketLeakage`:
the half-2 follow-up filed above (originally promoted to T-2101) landed on
the SAME id as an unrelated, already-real, already-landed SYS111 gates
ticket with its own live worktree. Verified by content: main's T-2101 was
"SYS111 capability-ratchet BEFORE snapshot drops frob.toml..." the whole
time; my worktree's T-2101 was my own "Detect a duplicate ticket id..."
ticket. Both guards that fired (`CrossTicketLeakage` at land, then
`TicketOwnershipViolation` when I tried to narrow "T-2101"'s scope, since
the real T-2101's lease belongs to its own SYS111 worktree) behaved
correctly -- the INPUT was corrupt, not the guards.

Root-caused the same way as every occurrence above: my worktree's view of
allocated ids was stale (last merged main before T-2101-SYS111 landed),
and `frob ticket promote`'s ceiling computation for MY draft used that
stale view. Resolved by: `git merge main` (bringing the real T-2101 in,
producing a real add/add conflict this time -- git itself caught it,
unlike the T-2083/T-2090 incident's silent resolution), keeping main's
side for the conflicted path, and re-filing my own content as a fresh
`frob ticket new` + `promote`, landing cleanly on T-2104 -- verified by
content in both the worktree and main before proceeding. This is the
strongest possible argument for this ticket's own priority: a critical
fix for silent id collisions was itself blocked from landing by exactly
the defect it fixes, three times over across today's session (T-2090,
T-2096/T-2098/T-2100's landing sequence, and this one).

## Occurrence 9: the SAME land's own internal merge lost the half-2 follow-up AGAIN

After landing T-2092 itself (verified: LAND-PROOF verified=True, content
confirmed via `git show --stat`), `frob ticket land --finish`'s cleanup
retry and then `git worktree remove` surfaced that `tickets/T-2104/ticket.md`
on main held a DIFFERENT, unrelated ticket's content ("A stale blocked_by
does not self-heal..."), not the half-2 follow-up filed and promoted to
T-2104 earlier in this session. Root-caused: after `frob ticket promote
T-draft-a77b91fb -> T-2104`, T-2092's own declared scope still listed
`tickets/T-2101/**` (the id BEFORE that promotion) -- `tickets/T-2104/**`
was never added. Land's own internal `merge main into worktree` step
(visible in the branch history as commits `c4d2b820c`/`7520ab473`) pulled
in a concurrently-filed, unrelated real T-2104 from main and the merge
silently took main's side for that path, because the file was outside
T-2092's declared scope and so was never protected/carried by the squash.
This is the SAME defect class as the whole T-2092 lineage, one level
removed: an out-of-scope ticket file, silently overwritten by an
in-process merge, no conflict, no warning -- caught only because I
happened to `grep` the content on main after landing instead of trusting
the id. My earlier content was still recoverable from the pre-merge branch
commit (`75dcc6a58:tickets/T-2104/ticket.md`, the worktree branch was NOT
deleted by `git worktree remove` even with `--force`, only the checkout
was) and refiled fresh, this time directly via `frob ticket new` from the
clean root main (no draft/promote step, so no scope-glob staleness window)
-- landed cleanly as **T-2105**, verified by content (`grep -m1 '^title:'
tickets/T-2105/ticket.md`) and a clean `git status --porcelain` on the
root both before and after.

Lesson for anyone renumbering/promoting a ticket file that a ticket's OWN
scope references by path: the scope glob must be updated to the NEW id
before land, or the renamed file falls outside the squash's protection
and an unrelated concurrent write can silently take it. This ticket did
not fix that generally (out of scope for T-2092's own file list) --
T-2105 is exactly the ticket to fix it, and this occurrence is now part
of its own evidence trail.

## `frob check --land-parity` gap for this land

`frob check --land-parity` did not complete during this session (spawn
budget truncation on this repo's full unscoped stage set) -- reported here
as a known, unmeasured gap for this land, NOT as a clean result. The
ticket-scoped `frob check --ticket T-2092 --only gates-fast/native/security`
runs (0 errors, verified via `scripts/check_summary.py`) are the only gate
measurement this land has; the coordinator's own post-land sweep is the
next real opportunity to catch anything land-parity would have caught.

Observed but NOT caused by this change: tests/test_tickets_collision.py::
TestPostArchiveReissueIncident::test_new_ticket_never_reissues_an_archived_id
fails intermittently when run as part of the full file, and consistently
passes in isolation or with -p no:randomly. Reproduced this both before and
after this ticket's own fix landed on the worktree, so it is pre-existing
test-order flakiness unrelated to renumber/allocator_lock, recorded here for
visibility.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_ledger_concurrency.py::TestRenumberVsNewTicketAllocationRace::test_renumber_and_concurrent_new_ticket_never_allocate_the_same_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)

### Acceptance amendments
- [2] remove: removed 'given a branch carrying a ticket file that a merge of main would overwrite with different content for the same id, when the merge happens during a land, then the collision is surfaced rather than silently resolved' (reason: Split per this ticket's own body ("If half 2 turns out to be genuinely
large, implement half 1, measure and report, and file half 2 as its own
ticket"). This criterion is the "detect a duplicate id after the fact"
half: it needs a real merge-time or history-scanning detector across
tickets/**/ticket.md, distinct from the allocator_lock fix this ticket
implements, and is genuinely separate engineering scope. Filed as
T-2101 with this session's own repro evidence cited.
; logan, 2026-08-10)
- [1] remove: removed 'given two ticket records that nonetheless claim the same id, when the ledger is loaded or checked, then this is reported as an error rather than silently resolved by picking one' (reason: Split per this ticket's own body ("If half 2 turns out to be genuinely
large, implement half 1, measure and report, and file half 2 as its own
ticket"). This criterion is the "detect a duplicate id after the fact"
half: it needs a real merge-time or history-scanning detector across
tickets/**/ticket.md, distinct from the allocator_lock fix this ticket
implements, and is genuinely separate engineering scope. Filed as
T-2101 with this session's own repro evidence cited.
; logan, 2026-08-10)
- [10] remove: removed 'rejected on sight for this ticket.' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [9] remove: removed 'atomic claim primitive) closes this; a "verify first" remedy must be' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [8] remove: removed 'no matter how careful the check is. Only a real lock (or an equivalent' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [7] remove: removed 'landed first) -- check-then-claim across two roots/worktrees is not atomic' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [6] remove: removed 'T-2096 was free, both got the same correct answer, both claimed it, one' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [5] remove: removed 'correctly and diligently (occurrence 4: two agents independently checked' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [4] remove: removed 'including twice by agents who performed exactly that verification' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [3] remove: removed 'as a fix for this ticket. Measured FOUR TIMES in one day (2026-08-10),' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [2] remove: removed '(a checklist/procedural discipline, documentation, or manual double-check)' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
- [1] remove: removed 'DO NOT accept "verify the target id is free before renumbering/allocating"' (reason: Accidental split: --criterion-file split this single criterion into 10 by
newline instead of blank-line-delimited blocks (my mistake, not a policy
change) -- removing to re-add as one criterion.
; logan, 2026-08-10)
