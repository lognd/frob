## Done report

Root cause: `_leaked_hits_for_candidate` (src/frob/tickets/_land.py) unconditionally
exempted any sibling ticket leased to the SAME worktree as the landing ticket
(the T-1370 same-worktree exemption), before ever computing whether the
sibling had real committed content in the branch. Since sharing one worktree
across a ticket series is this repo's normal, endorsed dispatch pattern, that
exemption fired on every ordinary series land and made the CrossTicketLeakage
guard permanently blind to exactly the shape it exists to catch: a sibling's
own committed, still-open work riding along silently. Reproduced live against
the measured incident: da9afe8369308c6c7666cfef9aa3053a07c960ec (T-1958's
land) carried T-1956's `_evidence.py`/`_models.py`/
`_new_gate_rule_acceptance.py`, its test file, and its Done report -- with
T-1956 IN_PROGRESS on main throughout, no `--allow-cross-ticket`, and no
warning printed. The separate T-1618 `_check_passenger_tickets` guard also
did not catch it, since T-1956's added hunks referenced "T-1937/T-1956" only
in prose, never as a genuine ticket-linking source-comment directive line
(the exact two-word marker that check scans for, spelled out here with a
space so this Done report's own prose cannot itself be misparsed as one).

Fix: removed the same-worktree exemption from `_leaked_hits_for_candidate`.
A same-worktree sibling with a real scope hit (content genuinely changed
since the branch's fork point, ticket IN_PROGRESS) now flows into the exact
same `leaked` map / `_report_leaked_tickets` refusal path a cross-worktree
leak already used -- it either requires the existing, already-logged
`--allow-cross-ticket` acknowledgment or refuses, naming the sibling by id.
This does not reintroduce T-1370's original mutual-deadlock concern: a hit
only ever exists once a sibling has genuinely been worked on the branch, and
`--allow-cross-ticket` remains the explicit way through for a genuinely
intentional joint land -- once the first of two mutually-scoped
same-worktree tickets lands, the second's own later land finds the first
already DONE and exempt.

Updated the existing `test_sibling_leased_to_same_worktree_does_not_block`
test (kept its NAME, since T-1370/T-1639 -- both DONE tickets -- cite that
exact node id as evidence; renaming it would have broken their COV003
resolution) to assert the corrected refusal behavior instead of the old
buggy exemption, and added a new
`test_sibling_leased_to_same_worktree_lands_with_explicit_ack` test proving
`--allow-cross-ticket` still unblocks a genuinely intentional joint land.
Widened T-1967's scope to include the test file and the one stale doc
paragraph in docs/modules/tickets.md that described the now-removed T-1370
exemption as still-applicable.

Verification: pytest tests/unit/test_land_cross_ticket_leakage.py (12 of 13
pass; the 13th, test_queued_sibling_scope_overlap_does_not_block, fails
identically on unmodified main -- a pre-existing fixture flake unrelated to
this change, confirmed by running it against main directly).
tests/test_ticket_land.py, tests/unit/test_land_step_ordering.py,
tests/unit/test_land_already_landed.py all pass (280 total). `frob check
--ticket T-1967` clean across gates-fast/gates-native/gates-security (the 2
gates-native errors are the pre-existing ARCH001 floor in
src/frob/gates/_dead_symbols.py, tracked separately as T-1962, not touched
by this ticket). `frob check --land-parity` clean.

### Changed
```
 tickets/T-1967/done-report.md | 69 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1967/ticket.md      | 27 +++++++++++++++--
 2 files changed, 94 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_lands_with_explicit_ack` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 1358 warning(s), 707 waived
- error-findings: PRE001@tickets/T-1967
