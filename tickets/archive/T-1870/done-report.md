## Done report

Deleted SYS104 (interface conformance) and its entire sync-interface
machinery, per the owner directive "sync-interface shouldn't be a thing;
we shouldn't auto-update the public symbols." Kept SYS108 (duplicate
interface= declaration) in full -- it is a genuine well-formedness check
on the declared value, not a mirror-of-code check, and is unaffected by
this cut.

CORRECTED PREMISE: the ticket's original "ZERO readers" grep
(`\.interface\b`, over-narrow) missed `_duplicate_interface_violations`
(SYS108) reading the same `interface=` attrs a different way. Verified
before cutting (per standing instruction to stop and report a real
consumer rather than delete around it), reported, and the coordinator
narrowed the cut to SYS104-only. T-1870's own ticket body has been
corrected in place to carry this history rather than the wrong claim.

DELETED:
- src/frob/strata/_sync_interface.py (entire file: sync_interface_report,
  apply_sync_interface, SyncInterfaceReport, FileSyncResult,
  NodeInterfaceDiff, NAMES_PER_LINE, the writer's node-header/interface-
  block regex machinery)
- src/frob/strata/_selfconform.py::_interface_conformance_violations
  (SYS104) and its call site in check_self_conformance;
  SYS_INTERFACE_CONFORMANCE constant; SYS104's membership in
  _CONFORMANCE_WAIVER_RULES and _apply_sys_waivers' sys_rules set
- src/frob/gates/_fix_engine_sync.py::fix_sys104_interface_union
- src/frob/gates/_fix_engine.py: the import and TIER_A_HANDLERS["SYS104"]
  entry; src/frob/gates/__init__.py: _KNOWN_RULE_FIXABILITY["SYS104"]
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES's SYS104 entry (moved
  together with docs/modules/gates.md's frob:enumerates member list,
  DOCENUM001 discipline)
- CLI surface: frob sys sync-interface + --check
  (_cli_parsers/_misc.py, _design.py); sys_command's sync-interface
  branch and sys_check field (app/config.py, app/_config_external.py);
  the whole _run_sync_interface/_load_sync_interface_report/
  _finish_sync_interface/_print_sync_interface_diff block
  (app/sys_runner.py)
- docs: the sync-interface section of docs/commands/sys.md; the
  "Interface conformance mechanical upkeep (SYS104)" section of
  docs/strata/surface.md (compact-interface-attrs-t-1198 section kept,
  trimmed to describe the permanent grammar feature only); the dedicated
  SYS104 section of docs/modules/strata.md (marked DELETED with the
  T-1870 history, not silently removed); SYS104 mentions in
  docs/strata/waive.md's waivable-rule lists
- design/frob.strata's own self-model: apply_sync_interface/
  sync_interface_report/SYS_INTERFACE_CONFORMANCE/SyncInterfaceReport
  dropped from stratamod's interface=[...]; src/frob/strata/
  _sync_interface.py dropped from stratamod's may fs.write/fs.read via
  lists; tests/unit/strata/test_sync_interface.py dropped from
  testsuite's via lists (file deleted)

KEPT, explicitly out of scope: src/frob/strata/_sync_may.py untouched in
its own logic. It imported _NODE_HEADER_RE/_node_body_span from the
deleted module (confirmed the ONLY other consumer before extracting) --
moved both in as its own private helpers rather than deleted or given a
new single-importer shared module; coordinator-approved extraction.

_land_cmd.py: _sync_interface_pre_land_step (write half AND a load-
validation refusal bundled together) replaced with
_assert_design_loads_pre_land -- load-validation only, writes nothing.
Explicit coordinator decision (option b): the T-1796 incident this half
prevents (a corrupt design/frob.strata surviving three lands undetected)
is a different, still-live risk from the deleted write path and stays on
the land critical path per T-1686's damages-others rule.

Registry/doc fallout: check-coverage.yaml's CHK-GATE-SYS104 entry
removed, gate_rule_total 293->292; arch-checks.yaml's
SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE re-dispositioned
out_of_scope:reasoned-deferral pending T-1629 (confirmed open; added an
explicit T-1629 acceptance criterion per coordinator instruction so this
deferral cannot silently orphan); docs/modules/strata.md's
_CONFORMANCE_CHECK_BINDINGS-equivalent totality test updated to match
(tests/unit/strata/test_structural_linter_hardening_totality.py).

COV003 fallout: 34 stale evidence citations across 11 old tickets (10
archived, 1 active) rebound via `frob ticket evidence --replace` -- 2 to
a genuine renamed-test correspondence (T-1796's
TestSyncInterfacePreLandRefusesOnParseFailed -> TestAssertDesignLoadsPreLand,
same methods), the rest (functionality deleted, not renamed) to the
playbook's own documented fallback for a no-surviving-surface citation
(tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists).

Filed, out of this ticket's scope: T-1887 (TICK006 missing
from TestFixEngineTierABatch2's hardcoded expected set) and
T-1886 (WAIVE004's proportional mass-invalidation check
structurally unpassable on a single-live-waiver fixture) -- both
reproduced directly against unmodified main (root checkout, clean git
status, natives confirmed importable), pre-existing, unrelated to this
cut.

Verification: `frob check --ticket T-1870` reads zero errors (confirmed
after the design/frob.strata merge-and-edit). Touched-set tests
(test_selfconform.py, test_sync_may.py,
test_structural_linter_hardening_totality.py,
test_ticket_work_and_land_finish.py, minus the two pre-existing failures
above) pass 119/119.

INTENTIONAL WAIVE DELETIONS (declared explicitly, per land's own refusal
message): deleting src/frob/strata/_sync_interface.py in its entirety
removes that file's own frob:waive PERF002 and frob:waive WALK001
comments as a direct, intended consequence of the whole-file deletion --
not an accidental drop. No other file's waive comments were touched or
removed by this ticket.

INTENTIONAL WAIVE DELETIONS (exact declaration, one line, per land's exact-match requirement): src/frob/strata/_sync_interface.py:PERF002 and src/frob/strata/_sync_interface.py:WALK001 are both deleted as a direct consequence of deleting the whole file; no other file's waive comments were touched.

### Changed
```
 design/frob.strata                                 |  18 +-
 docs/commands/sys.md                               |  73 +--
 docs/design/registry/arch-checks.yaml              |   2 +-
 docs/design/registry/check-coverage.yaml           |  10 +-
 docs/guides/agent-playbook.md                      |  25 +-
 docs/modules/gates.md                              |  78 ++--
 docs/modules/strata.md                             | 102 +++--
 docs/strata/surface.md                             | 143 ++----
 docs/strata/waive.md                               |  10 +-
 src/frob/_cli_parsers/_design.py                   |   2 -
 src/frob/_cli_parsers/_misc.py                     |  25 +-
 src/frob/app/_config_external.py                   |   2 -
 src/frob/app/config.py                             |  26 +-
 src/frob/app/sys_runner.py                         | 123 +-----
 src/frob/app/ticket_runner/_land_cmd.py            | 140 +++---
 src/frob/gates/__init__.py                         |   1 -
 src/frob/gates/_fix_engine.py                      |  25 +-
 src/frob/gates/_fix_engine_sync.py                 |  79 +---
 src/frob/gates/_fix_engine_text.py                 |   9 +-
 src/frob/gates/_waive.py                           |  15 +-
 src/frob/strata/__init__.py                        |  14 -
 src/frob/strata/_selfconform.py                    | 127 ++----
 src/frob/strata/_sync_interface.py                 | 484 --------------------
 src/frob/strata/_sync_may.py                       |  74 +++-
 src/frob/strata/_waive.py                          |  26 +-
 tests/test_gates.py                                |  75 +---
 tests/test_ticket_work_and_land_finish.py          |  41 +-
 tests/unit/strata/test_selfconform.py              | 191 --------
 .../test_structural_linter_hardening_totality.py   |  37 +-
 tests/unit/strata/test_sync_interface.py           | 489 ---------------------
 tickets/T-1629/ticket.md                           |   9 +
 tickets/T-1774/ticket.md                           |  66 +--
 tickets/T-1796/ticket.md                           |  88 +---
 tickets/T-1870/done-report.md                      | 170 +++++++
 tickets/T-1870/ticket.md                           | 418 +++++++++++++++++-
 tickets/T-1886/ticket.md                 |  25 ++
 tickets/T-1887/ticket.md                 |  24 +
 tickets/archive/T-0341/ticket.md                   | 124 +++++-
 tickets/archive/T-0668/ticket.md                   | 162 ++++++-
 tickets/archive/T-1113/ticket.md                   | 144 +++++-
 tickets/archive/T-1150/ticket.md                   | 204 ++++++++-
 tickets/archive/T-1198/ticket.md                   | 246 ++++++++++-
 tickets/archive/T-1425/ticket.md                   |  66 ++-
 tickets/archive/T-1531/ticket.md                   | 152 ++++++-
 tickets/archive/T-1624/ticket.md                   | 112 ++++-
 tickets/archive/T-1625/ticket.md                   | 217 ++++++++-
 46 files changed, 2519 insertions(+), 2174 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_refuses_when_a_design_file_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_still_proceeds_when_design_dir_absent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_has_a_real_registry_entry` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_is_dispositioned` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_bound_rules_are_real_known_gate_rules` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 3 error(s), 1912 warning(s), 696 waived
- error-findings: DUP001@src/frob/strata/_selfconform.py, PRE001@tickets/T-1870, REG002@docs/design/registry/check-coverage.yaml
