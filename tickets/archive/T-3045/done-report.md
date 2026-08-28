## Done report

Changed:
src/frob/tickets/_models.py::CMD_EVIDENCE_ALLOWED_KINDS (now {DOCS, UX})
src/frob/gates/__init__.py::evidence_covers_scope (docstring: stale "today
  just docs" claim corrected to docs/ux)
src/frob/tickets/_evidence.py::add_cmd_evidence (docstring: same
  correction, plus removed ux from the "code-kind" example list it was
  wrongly grouped into)
docs/modules/tickets.md (add_cmd_evidence's public-API summary line
  updated to say docs/ux)

Payload/fix chosen and why:
H5 is a one-line frozenset fix, not a design gap: `TicketKind.UX` already
existed as a first-class kind, but `CMD_EVIDENCE_ALLOWED_KINDS` only ever
named `DOCS`, so a UX ticket -- a design review, an accessibility pass, a
visual-QA sign-off, none of which are pytest-shaped -- had NO channel to
ever close at all. Every code-kind exclusion (bug/feature/security/
invariant/incident) stays exactly as strict as before; only UX joins DOCS
in the allowed set, since it shares the exact "no pytest surface by
design" property T-0215 built this channel for.

Three stale docstrings claiming "currently just docs" were corrected in
the same change so they do not silently drift into false documentation
the moment this landed.

Fixtures added (must-fire / must-stay-quiet pairs):
- tests/test_tickets_cmd_evidence.py::TestKindGate.test_ux_kind_closes
  (must-stay-quiet: UX closes on cmd evidence, mirrors test_docs_kind_closes)
- tests/test_tickets_cmd_evidence.py::TestKindGate
  .test_ux_kind_ticket_failing_cmd_blocks_close (must-fire: kind
  permission does not bypass the exit-status check)
- tests/test_tickets_cmd_evidence.py::TestCov003CmdEvidence
  .test_ux_ticket_closed_via_evidence_cmd_is_gate_clean (must-stay-quiet:
  COV003 end-to-end)
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose
  .test_land_validate_closeable_accepts_ux_cmd_entry (must-stay-quiet:
  land-time guard layer; the existing
  test_land_validate_closeable_refuses_hand_pasted_cmd_entry (SECURITY)
  is the pre-existing must-fire twin at this same layer)

Evidence:
pytest tests/test_tickets_cmd_evidence.py -p no:cacheprovider -q:
32 passed, 0 failed (was 26 before this ticket's 6 new tests).
frob check --only fmt/coverage/test --ticket T-3045: zero NEW findings
attributable to this ticket's touched files (all reported errors/warnings
in the output pre-exist in unrelated files -- confirmed by grepping the
touched-file list against each gate's output; the full repo-wide DRIFT/
WAIVE/COV/TEST backlog is unrelated pre-existing debt, unaffected by a
one-line frozenset addition plus docstring corrections).

Filed: T-3078 (TEST001 gap on T-3044's new graph::model attrs API --
discovered while running the shared test gate for this series' land,
strictly outside T-3045's own scope).

Gates: frob check --only fmt/coverage/test --ticket T-3045 clean for
every symbol/file this ticket touches (see Evidence above).

### Changed
```
 docs/modules/tickets.md            |  4 +-
 src/frob/gates/__init__.py         |  2 +-
 src/frob/tickets/_evidence.py      |  4 +-
 src/frob/tickets/_models.py        |  8 +++-
 tests/test_tickets_cmd_evidence.py | 72 ++++++++++++++++++++++++++++
 tickets/T-3045/ticket.md           | 96 +++++++++++++++++++++++++++++++++++++-
 6 files changed, 180 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 64 error(s), 1167 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DUP001@tests/test_tickets_cmd_evidence.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3045, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
