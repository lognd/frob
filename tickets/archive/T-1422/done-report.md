## Done report

Added a supported way to correct or drop an acceptance criterion instead
of the two workarounds that were actually used this session: hand-editing
tickets.md (which corrupted the ledger for real -- a space-hash inside a
plain YAML scalar started a comment and took the whole gate layer down)
and filing a successor ticket to carry the same work under a new id.

frob.tickets.amend_acceptance/remove_acceptance (src/frob/tickets/
_accept.py, new module, same per-family split pattern _scope.py
established for mutate_scope) both require a non-blank --reason, append
an AcceptanceAmendmentEntry to the ticket's new acceptance_amendments
audit tuple (old text always preserved, never edited/removed once
written), and are refused outright on a ticket already DONE/DROPPED.
Wired through `frob ticket accept <id> --amend INDEX --text TEXT
(--reason TEXT | --reason-file PATH)` and `--remove INDEX (--reason TEXT
| --reason-file PATH)` (frob.app.ticket_runner._mutate._accept_amend/
_accept_remove), --reason-file routing text through a path per the
backtick-in-inline-flag hazard this repo's hooks already reject.

Surfaced in two places, never buried: `frob ticket show` prints an
acceptance_amendments: block after the acceptance list
(_query.py::_render_acceptance_amendments), and compose_done_report
renders an "### Acceptance amendments" section whenever
Ticket.acceptance_amendments is non-empty (_reporting.py), wired through
set_done_report so a ticket's own Done report carries its amendment
history automatically.

Modelled the two real incidents named in the ticket body directly as
tests: a mis-specified criterion (T-1411's criterion [0] shape, amend)
and an unsatisfiable-by-construction criterion (the ten burn-down
tickets' "0 findings under package X" shape, remove). A dedicated test
also proves the ledger stays parseable after an amendment whose reason
text contains a hash, colon, and quotes -- the exact class of input that
broke tickets.md by hand.

Named the abuse case plainly in docs/modules/tickets.md's new section:
amending is a correction when the criterion was wrong, goalpost-moving
when it was right and the work fell short; this cannot be automated,
only made reviewable via the mandatory reason and the two surfacing
points above.

Scope drifted from the ticket's declared src/frob/app/ticket_runner/
_metadata.py (no such file exists) to the real files this required --
narrowed via `frob ticket scope` with a stated reason before touching
anything, per playbook section 4.

Out-of-scope discovery, filed as a draft (renumbers at land):
T-1425 -- `frob sys sync-interface` only auto-rewrites `node`
interface= blocks, silently skipping `store` blocks (e.g. tickets_ledger)
even though the SELFAUDIT/SYS104 gate correctly flags drift on them; had
to hand-add the 4 new interface= lines to design/frob.strata's store
block since the tool itself reported "0 drifted" and refused to fix it.

### Changed
```
 design/frob.strata                         |  12 ++
 docs/modules/tickets.md                    |  74 +++++++
 src/frob/_cli_parsers/_ticket/_metadata.py |  75 +++++--
 src/frob/app/config.py                     |  14 ++
 src/frob/app/ticket_runner/_mutate.py      | 132 +++++++++++-
 src/frob/app/ticket_runner/_query.py       |  28 ++-
 src/frob/tickets/__init__.py               |   7 +
 src/frob/tickets/_accept.py                | 278 +++++++++++++++++++++++++
 src/frob/tickets/_models.py                |  60 ++++++
 src/frob/tickets/_reporting.py             |  60 +++++-
 tests/test_tickets_acceptance.py           | 319 ++++++++++++++++++++++++++++-
 tickets.md                                 | 286 +++++++++++++++++++++++++-
 12 files changed, 1311 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_replaces_text_and_records_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_reason_containing_hash_colon_and_quotes_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_replaces_text` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_renders_amendment_and_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_done_report_renders_amendment_section` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_done_report_omits_section_when_no_amendments` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_on_terminal_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_refuses_on_terminal_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_preserves_existing_evidence_binding` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_empty_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_out_of_range_index` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_drops_criterion_and_records_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_remove_drops_criterion` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_without_reason_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_and_remove_together_is_rejected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 11 error(s), 645 warning(s), 708 waived
- error-findings: ARCH001@src/frob/app/_config_external.py, DRIFT002@docs/guides/agentic-workflow.md, DRIFT002@docs/modules/arch.md, DRIFT002@tests/unit/test_arch.py, DRIFT002@tests/unit/test_ticket_runner_land_cmd_flags.py, INV006@src/frob/_cli_parsers/_ticket/__init__.py, INV006@src/frob/_cli_parsers/_ticket/_closeout.py, INV006@src/frob/_cli_parsers/_ticket/_progress.py, INV006@src/frob/_cli_parsers/_ticket/_query.py, INV006@src/frob/tickets/_accept.py, PRE001@tickets/T-1422
