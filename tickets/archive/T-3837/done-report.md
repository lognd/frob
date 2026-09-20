## Done report

T-3837 (F-032): --accepts N on frob ticket evidence/close/reverify was 0-based through T-0572..T-0844. 0-based indexing plus an out-of-range check that only rejected i<0 or i>=len(acceptance) let a caller who counts acceptance criteria 1, 2, 3... (as frob ticket show's own [1] .../[2] ... display invites) pass an index off by one from what they meant, land INSIDE the valid range, and silently bind evidence to the WRONG criterion -- a mis-binding indistinguishable from a correct one in the ticket record, the done report, and every downstream coverage check. Out-of-range rejection alone cannot catch this: the wrong index is still a valid index.

Fix: switched --accepts to 1-based indexing everywhere (add_evidence, add_cmd_evidence, the CLI parsers for evidence/close/reverify, the show display's [N] bracket numbering, and every remediation/hint message that documented the old contract), so the index a caller passes now matches exactly what frob ticket show prints. The out-of-range refusal stays loud and typed (Err(AcceptanceIndexOutOfRange)), now checked against the 1..N range, with 0 explicitly rejected as a likely leftover habit from the old scheme rather than silently binding or clamping.

MUST-FIRE: TestAcceptsOneBasedMisBinding proves the exact old mis-binding shape is now impossible (accepts=[2] on a 4-criterion ticket binds the SECOND criterion, matching the [2] display, never the third) and that 0/out-of-range indices refuse loudly rather than binding silently. MUST-STAY-QUIET: ordinary first/last-position binding and the show display's bracket numbering are covered and pass.

Filed: none (no out-of-scope discoveries this ticket).

Two DOC006 findings on tickets/T-3807 and tickets/T-3843 remain under --ticket T-3837 -- confirmed pre-existing on main via git show, unrelated to this ticket's scope.

frob.lock could not be added to this ticket's scope (leased by unrelated in-progress T-3799, Windows PATHEXT work) so the AFFECT001/DRIFT001 doc-drift ack could not be written to frob.lock; docs/modules/tickets.md was updated to reflect the fix and the two affected symbols carry a frob:waive AFFECT001/DRIFT001 explaining the lease conflict (same precedent as frob/gates/_wire.py's existing T-2466 waiver).

### Changed
```
 docs/modules/tickets.md                    |   7 +-
 src/frob/_cli_parsers/_ticket/_closeout.py |  20 ++--
 src/frob/app/config.py                     |   7 +-
 src/frob/app/ticket_runner/_close_cmd.py   |   4 +-
 src/frob/app/ticket_runner/_query.py       |  12 ++-
 src/frob/app/ticket_runner/_verify.py      |   7 +-
 src/frob/tickets/_evidence.py              |  89 +++++++++++-----
 src/frob/tickets/_land_merge.py            |   3 +-
 tests/test_tickets_acceptance.py           | 160 +++++++++++++++++++++++++++--
 tests/test_tickets_evidence_cli.py         |   6 +-
 tickets/T-3837/ticket.md                   |  45 ++++++++
 11 files changed, 299 insertions(+), 61 deletions(-)
```

### Evidence
- `tests/test_tickets_acceptance.py::TestAcceptsOneBasedMisBinding::test_must_fire_the_old_0_based_third_criterion_index_now_binds_second` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptsOneBasedMisBinding::test_must_fire_zero_is_a_loud_out_of_range_refusal_not_a_silent_bind` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptsOneBasedMisBinding::test_must_fire_one_past_the_end_is_a_loud_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptsOneBasedMisBinding::test_must_stay_quiet_first_and_last_1_based_positions_bind_correctly` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptsOneBasedMisBinding::test_must_stay_quiet_show_render_uses_matching_1_based_brackets` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAddEvidenceAccepts::test_accepts_binds_evidence_onto_the_named_criterion` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAddEvidenceAccepts::test_accepts_out_of_range_rejects_the_whole_batch` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestCloseGate::test_binding_the_criterion_via_accepts_then_closing_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_from_external_carries_accepts_from_parsed_argv` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 2 error(s), 4444 warning(s), 924 waived
- error-findings: DOC006@tickets/T-3807/ticket.md, DOC006@tickets/T-3843/ticket.md
