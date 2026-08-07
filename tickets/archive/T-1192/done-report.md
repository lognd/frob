## Done report

T-1192's 34-file LARGE001 residue list is too large for one land; picked
ONE cohesive, low-risk real split this land: split the provisional-draft-
id finalization pair (finalize_draft/finalize_draft_for_land plus their
shared private critical-section helper _finalize_draft_for_land_locked)
out of src/frob/tickets/_new_renumber.py (847 -> 691 lines, now under the
800-line LARGE001 threshold) into a new src/frob/tickets/_draft_finalize.py
(198 lines). frob.tickets.__init__ now imports both public names from the
new module directly; _draft_finalize.py imports _next_ticket_id back from
_new_renumber.py for its own use. T-1103's package-level renumber_one
re-import indirection (so a test monkeypatching frob.tickets.renumber_one
is observed) is preserved verbatim from the caller's new location.

docs/modules/tickets.md's frob:describes anchor and two frob:tests
directives in tests/test_tickets_collision.py naming the old
`_new_renumber.py::finalize_draft`/`finalize_draft_for_land` path were
repointed to `_draft_finalize.py`; scope was extended to cover those two
files plus tests/test_tickets_ledger_concurrency.py (which also carries a
frob:tests directive for finalize_draft, already correctly pointed since
it names the function, not the old path).

This closes 1 of 34 files on T-1192's own residue list -- LARGE gate count
dropped 48 -> 47 warnings. The other 33 files (including the two
explicitly-flagged-as-needing-a-follow-up vet/_capability.py and
vet/_capability_registry.py) remain unowned; re-filed as a follow-up
ticket rather than closing silently, per TICK011 and this drive's own
one-subsystem-per-land discipline (T-1072/T-1074/T-1186/T-1187/T-1188/
T-1189 precedent).

Also repointed src/frob/gates/_fix_engine.py::fix_tick002_renumber's
deferred `from frob.tickets._new_renumber import finalize_draft` (an
out-of-scope caller of the moved function land discovered) to
`frob.tickets._draft_finalize`, and updated its docs/modules/gates.md
description to match.

### Changed
```
 tickets.md | 128 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 127 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_finalize_draft_rewrites_a_sibling_ticket_done_report_prose` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view` (pytest node id, verified passing when recorded)
- `tests/test_tickets_ledger_concurrency.py::TestFinalizeDraftAllocationRace::test_two_concurrent_finalize_draft_calls_get_distinct_ids` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 6448 warning(s), 671 waived
- error-findings: none (measured, zero errors)
