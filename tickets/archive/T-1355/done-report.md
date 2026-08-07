## Done report

Implemented the "refuse loudly, force an explicit decision" design option
from the ticket's design questions -- the other two (restrict the squash
merge to scope; park paused work on a separate branch) both change land's
core merge semantics or the standing series-worktree workflow itself,
neither of which is a safe change to make unilaterally inside one leaf
ticket's declared scope.

Added `_check_cross_ticket_leakage` (src/frob/tickets/_land.py), run as a
new step in `_land_precheck`, BEFORE any git mutation: diffs `worktree`'s
branch against main's tip for committed files, then cross-references that
changeset against every OTHER ticket in the worktree's own ledger (the one
place that already knows about a same-worktree sibling ticket pre-merge --
a still-open sibling generally does not exist in root's ledger at all
until this land's own squash-splice would introduce it). Any changed file
covered by another OPEN (non-terminal) ticket's declared scope refuses the
land with `LandError.CrossTicketLeakage`, naming the sibling ticket and
the exact leaked paths. Root's ledger is consulted as the authoritative
source for TERMINAL state when it already knows the ticket (a ticket
landed done through its own earlier `frob ticket land` call must not
block an unrelated land just because the worktree's own pre-pull copy
still shows in-progress). The ledger/archive files themselves are
excluded from the leakage scan -- they are implicitly in every ticket's
scope (`scope_matches`'s always-in-scope rule) and are expected to change
on every land, so including them made the check false-positive on every
single multi-ticket-worktree land regardless of any real leakage.

Added `allow_cross_ticket` (default `False`) as the escape hatch for a
genuinely intentional joint landing, threaded through `land()` ->
`_land_locked` -> `_land_precheck`, mirroring `skip_mutation_evidence`'s
existing pattern (runs and logs either way, never silently bypasses).

Reproduced the real T-1352/T-1276 incident directly in a new test file
(tests/unit/test_land_cross_ticket_leakage.py, real git fixture repos, no
mocks -- test_ticket_land.py is owned by a concurrent agent so this had
to be a new file): a worktree hosting two tickets, one committed and
paused `in-progress`, one independent and ready to land -- confirms the
refusal, the override, the no-op single-ticket case, and that an
already-DONE-on-root sibling never blocks.

Disclosed cuts:
- `docs/modules/tickets.md` and `design/frob.strata` could not be updated
  for this ticket: both files are currently leased by T-1358 (worked
  earlier in this same series, left open per this dispatch's instruction
  to stop after commit rather than close). `frob sys sync-interface`'s
  own edit to design/frob.strata (registering the new TestCrossTicketLeakage
  symbol) was reverted for the same reason. This produces one expected
  SELFAUDIT001 finding (the new test class not yet in the design
  interface) and contributes to three SCOPE001 findings (design/frob.strata
  plus T-1358's own _land_release.py/test file, both present on this
  shared branch but outside T-1355's declared scope) -- all resolve
  automatically once T-1358 lands and its lease releases. This is exactly
  the lease-deadlock class T-1356 (next in this series) is scoped to fix.
- No CLI flag (`--allow-cross-ticket`) was wired for the new
  `allow_cross_ticket` parameter -- CLI wiring lives in
  src/frob/app/ticket_runner/_land_cmd.py and src/frob/_cli_parsers/**,
  both outside T-1355's declared scope (src/frob/tickets/_land.py,
  src/frob/tickets/_models.py, docs/modules/tickets.md). The library-level
  override is fully functional and tested; a follow-up ticket should wire
  the CLI flag.

### Changed
```
 design/frob.strata                        |   3 +
 docs/modules/tickets.md                   |  15 +++
 src/frob/tickets/_land_release.py         | 140 ++++++++++++++++++----
 tests/unit/test_land_release_coherence.py | 180 ++++++++++++++++++++++++++++
 tickets.md                                | 191 +++++++++++++++++++++++++++++-
 5 files changed, 505 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_ticket_already_done_on_main_does_not_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 694 warning(s), 706 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w1-land/src/frob/tickets/_land.py:1229, SELFAUDIT001@design
