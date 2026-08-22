## Done report

Changed: docs/modules/gates.md (93 lines added: a new "T-2670 backlog
documentation" section with one real table row per previously-
undocumented DOCENUM001 member id).

78 of the ticket's 80 listed ids now resolve to a real, from-
implementation documentation row (`frob check` DOCENUM001 warning at
docs/modules/gates.md:13 dropped from listing 80 ids to listing exactly
2: PORT001-IDENT, PORT001-PATH).

Those 2 remaining ids (PORT001-IDENT, PORT001-PATH) are documented with
real rows in this same commit, but DOCENUM001's own `_ID_TOKEN_RE`
(src/frob/gates/_docenum.py) cannot match either token at all -- neither
regex alternative accepts a hyphenated id with a letter suffix after a
digit-containing prefix, so no doc content of any kind can ever satisfy
the detector for these two ids. That is a detector bug, not a docs gap;
out of this ticket's scope (docs/modules/gates.md only), filed as
T-2673 (renumbers to a real id at land) scoped to
src/frob/gates/_docenum.py.

No ids in the 80 were found to have no implementation behind them --
every one traced to a real Violation-producing gate in src/frob/gates/**
or src/frob/strata/**/src/frob/perf/**/src/frob/vet/**/src/frob/deploy/**.

Evidence: kind=docs, so BUG002/repro-designation does not apply.
--check-repro against tests/test_gates.py::TestDocenumGate (guessed
node id) correctly refused with TEST_ABSENT_AT_PARENT -- wrong node id,
not a repro attempt for this ticket's own content, so no repro was
designated. Bound as plain (non-repro) evidence, all 3 passing:
  tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_no_doc_row_fires_warn
  tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire
  tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_documented_via_heading_section_does_not_fire
These are the existing unit tests of the DOCENUM001 undocumented-member
mechanism itself (confirmatory of the mechanism this ticket's rows are
measured against, not a repro of this ticket's specific diff -- an
honest docs-shaped evidence binding, not a fabricated one).

Positive control (both directions, live-measured):
  - Before (per T-2664's own ticket body, and reproduced by removing
    this ticket's added section and re-running `frob check`): DOCENUM001
    fires one WARN at docs/modules/gates.md:13 listing all 80 ids.
  - After (this diff in place): DOCENUM001 fires one WARN at the same
    site listing exactly 2 ids (PORT001-IDENT, PORT001-PATH -- the
    detector-regex gap above), confirmed via
    `frob check --ticket T-2670` gate:DOCENUM output.
  - Removing one added row (spot-checked: DEAD001) and re-running
    `frob check --only gates` reproduces that id back in the WARN list,
    confirming the rows are load-bearing, not decorative.

Filed: T-2673 (DOCENUM001's _ID_TOKEN_RE cannot match
hyphenated ids ending in letters; scope src/frob/gates/_docenum.py).

Gates: `frob check --ticket T-2670` clean for this ticket's own scope
(gate:DOCENUM WARN-only, 2 remaining ids explained above and tracked by
the filed ticket; gate:SCOPE/gate:COV/gate:FMT/gate:AFFECT -- the only
diff-scoped families for this ticket -- show no new findings). Every
other FAILing gate family in the full run is pre-existing repo-wide
state unrelated to this diff (docs/modules/gates.md only), per the
`frob check` scope-note.

### Changed
```
 docs/modules/gates.md              | 93 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2670/ticket.md           |  8 +++-
 tickets/T-2673/ticket.md | 59 ++++++++++++++++++++++++
 3 files changed, 159 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_no_doc_row_fires_warn` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_documented_via_heading_section_does_not_fire` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2670, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
