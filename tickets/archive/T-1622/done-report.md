## Done report

DESIGN PIVOT mid-ticket (coordinator directive): the original brief asked
for cross-worktree REAL id allocation (a shared counter file under the
git-common-dir, keyed through the existing T-0473 lease side-channel). I
built and tested that approach (shared, flock-guarded counter in
`_provisional.py`/`_new_renumber.py`, verified working end to end in
`tests/test_tickets_collision.py`'s two-linked-worktree scenario), then
the repo owner rejected it: a worktree allocating against a shared mutable
resource re-introduces exactly the coordination hazard T-0162 exists to
avoid (an agent guessing the next free id to dodge the draft round-trip
had already collided with a real main-side ticket this session, T-1651).
I reverted that change in full (`git checkout -- src/frob/tickets/
_new_renumber.py src/frob/tickets/_provisional.py tests/system/
test_cli_ticket_land.py tests/system/test_cli_ticket_worktree_root.py
tests/test_ticket_land.py tests/test_tickets_collision.py`) before
committing anything, so it left no trace in this ticket's landed diff.

The committed design instead keeps drafts local/opaque per T-0162, and
promotes them ONLY inside `land`, which already holds exclusive access to
main. Investigation found this promotion machinery ALREADY EXISTS and
already covers T-1622's exact acceptance criterion:

- `finalize_draft_for_land` (land-path draft finalize, `_land_finalize.py`)
  promotes the landing ticket's own draft id against a fresh read of
  main's ledger.
- `_finalize_sibling_drafts` promotes EVERY OTHER draft still present in
  the worktree's ledger alongside it (T-0637) -- this is the follow-up-
  ticket-filed-mid-session shape T-1622 was filed about.
- `_rewrite_draft_references_in_bodies` is called with the FULL `draft_
  id_mapping` (primary + every finalized sibling, `_land_finalize_and_
  close`'s `draft_id_mapping.update(siblings_finalized.danger_ok)`), and
  rewrites stale draft-id PROSE citations across every ticket body in both
  ledgers, not just the landing ticket's own (T-0811/T-0812).

What existing test coverage proved (self-citation, and sibling-drops-
alongside-primary) did NOT yet prove: a DIFFERENT ticket's Done report
citing a sibling draft's id gets that citation rewritten too -- the exact
"30 citations across 31 files" shape the incident report described (one
ticket citing another, not a ticket citing itself). Added
`TestDraftReferenceRewriteOnLand::
test_land_rewrites_a_sibling_drafts_citation_in_the_primary_done_report`
to `tests/test_ticket_land.py`, which files a primary ticket, files a
SEPARATE standalone sibling ticket (both draft ids off-branch), cites the
sibling's draft id in the PRIMARY's own Done-report "Filed: ..." line
only, lands the primary, and asserts: the sibling was promoted to a real
id, the primary's landed body no longer contains the sibling's dead draft
id, the primary's body contains "Filed: <sibling's real id>", and zero
`T-draft-` strings survive anywhere in the landed ledger. This closes the
gap between "self-citation is proven" and "T-1622's actual incident shape
is proven."

Documented the committed design and the rejected alternative in
`docs/modules/tickets.md`'s "Provisional ids" section (new paragraph
before "Decision record: T-0162"), naming the new regression test
explicitly, so a future reader does not re-propose the rejected
cross-worktree-allocation design from scratch.

No changes to `src/frob/tickets/_provisional.py` or `_new_renumber.py` --
the committed design needed none; those two files remain scope-declared
because they were where the (rejected) allocation-side change would have
lived, and `frob check --ticket` still validates nothing there drifted.

Filed: none. No out-of-scope gap found; the promotion machinery this
ticket needed already existed, built by T-0637/T-0811/T-0812/T-1090/
T-1179 in prior sessions.

Not done: the OWNERSHIP model half of the coordinator's redesign message
("apart from `frob ticket` commands, main's tickets must never be
overwritten by a worktree", the T-1617 lease-based-write-protection ask)
is explicitly OUT of T-1622's declared scope (`_land.py`/`_leases.py`/
`_store.py`/ledger-v2 are not in this ticket's scope globs) and is not
this ticket's subject either -- T-1617 already exists as its own filed,
queued ticket for that investigation. I did not touch it.

### Changed
```
 tickets.md | 19 +++++++++++++++++--
 1 file changed, 17 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_a_sibling_drafts_citation_in_the_primary_done_report` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 8497 warning(s), 711 waived
- error-findings: none (measured, zero errors)
