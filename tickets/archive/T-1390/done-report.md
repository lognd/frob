## Done report

Fixed CrossTicketLeakage's declared-scope-only matching (T-1355/T-1370's
_find_leaked_tickets in src/frob/tickets/_land.py). A sibling ticket's
declared scope matching a changed path is no longer sufficient to flag
a leak: the sibling's own ledger record must ALSO have changed on this
branch since it forked from base_ref (new _ledger_ticket_at_merge_base,
compared via pydantic value equality against the worktree's current
copy). An unrelated open ticket that merely declares a broad scope
(src/**, tests/**) but never actually got started/worked on this branch
now lands cleanly without --allow-cross-ticket; a genuine leak (the
sibling's ledger record moved here -- the real T-1352/T-1276 shape)
still refuses exactly as before. T-1370's same-worktree-lease exemption
is untouched. Split _find_leaked_tickets's per-candidate body into
_leaked_hits_for_candidate to clear an ARCH001 line-count violation the
added logic introduced.

Verified: tests/unit/test_land_cross_ticket_leakage.py (6/6, including a
new regression test for the false-positive class and the pre-existing
genuine-leak refusal test, both passing) and tests/test_ticket_land.py
(202/202) both clean. ruff check/format and ty clean on the touched
files. Every frob check gate family (39/39, chunked per agent-playbook.md
section 3b) reports 0 errors scoped to T-1390.

Disclosed incident: while landing, an accidental git stash pop (against
playbook guidance) popped a different worktree's stash entry onto this
shared main checkout; the conflicted pop was reverted cleanly via
git reset --merge HEAD without dropping the other agent's stash entry.
Separately, this ticket's own in-progress code landed on main under an
unrelated commit's message (c2fd45da, a ticket-filing commit) before a
follow-up commit (7a402998) corrected the ARCH001 split on top -- filed
T-1403 to investigate the mechanism and flag the misleading history.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_declaring_broad_scope_but_untouched_does_not_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 432 warning(s), 697 waived
- error-findings: none (measured, zero errors)
