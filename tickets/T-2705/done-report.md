## Done report

Changed:
src/frob/gates/_doclink_docanchor.py::_makefile_targets (now takes a
Makefile path directly, not root)
src/frob/gates/_doclink_docanchor.py::_makefiles_for_doc (new)
src/frob/gates/_doclink_docanchor.py::_doc010_scan_doc (rewired to
resolve against the doc's own Makefile-resolution chain, cached across
the scan)
src/frob/gates/_doclink_docanchor.py::docmake_gate (updated docstring,
per-scan target cache)

Evidence:
tests/test_gates.py::TestDocmakeGate::test_nested_project_target_resolves_against_nested_makefile
tests/test_gates.py::TestDocmakeGate::test_nested_project_bogus_target_still_fires
tests/test_gates.py::TestDocmakeGate::test_root_level_doc_still_resolves_against_root_makefile
tests/test_gates.py::TestDocmakeGate::test_nested_doc_falls_back_to_root_target_when_absent_nested
(full TestDocmakeGate class re-run: 7/7 pass, including the 3
pre-existing tests unchanged)

Validated against the real consumer repo (/home/logan/projects/aprog-public,
read-only): `frob check --only docmake` there dropped from the reported
`slidegen/docs/scripts.md:231 make preview` false positive to 0 DOC010
errors.

Filed: none

Gates: ruff/ty clean on touched files; full TestDocmakeGate suite green.

### Changed
```
 src/frob/gates/_doclink_docanchor.py |  62 +++++++++++++++++---
 tests/test_gates.py                  | 108 ++++++++++++++++++++++++++++++++---
 tickets/T-2705/ticket.md             |  21 ++++++-
 3 files changed, 175 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDocmakeGate::test_nested_project_target_resolves_against_nested_makefile` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocmakeGate::test_nested_project_bogus_target_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocmakeGate::test_root_level_doc_still_resolves_against_root_makefile` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocmakeGate::test_nested_doc_falls_back_to_root_target_when_absent_nested` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 45 error(s), 1544 warning(s), 680 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DUP001@tests/test_gates.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2705, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
