## Done report

Changed:
src/frob/strata/_parse.py::strata_core_import_error
src/frob/strata/_parse.py::parse_module
src/frob/strata/_facts.py::strata_core_import_error
src/frob/strata/_facts.py::_validate_build_facts_preconditions
src/frob/strata/_design_load.py::DesignLoadError
src/frob/strata/_design_load.py::_parse_one_design_file
src/frob/gates/_sys.py::_sys004

Evidence:
tests/unit/strata/test_parse.py::TestStrataCoreImportError::test_none_when_import_succeeded
tests/unit/strata/test_parse.py::TestStrataCoreImportError::test_names_the_real_exception_not_the_generic_guess
tests/unit/strata/test_parse.py::TestStrataCoreImportError::test_parse_module_log_names_captured_detail
tests/unit/strata/test_facts.py::TestFactsStrataCoreImportError::test_names_the_real_exception
tests/test_gates.py::TestSysGate::test_sys004_load_failure
tests/test_gates.py::TestSysGate::test_sys004_suppresses_sys001
tests/test_gates.py::TestSysGate::test_sys004_names_stale_native_as_likely_remedy
tests/test_gates.py::TestSysGate::test_sys004_names_missing_native_hint_when_genuinely_absent
tests/test_gates.py::TestSysGate::test_sys004_names_real_exception_when_strata_core_fails_differently

Positive controls (both directions, required by the ticket):
- genuinely-absent direction: strata_core=None with no captured import
  error still names the friendly not-installed hint, and the message
  does NOT claim an "actual import error" it never had
  (test_sys004_names_missing_native_hint_when_genuinely_absent, and
  verified live against the real consumer repo aprog-public via
  load_design_ids with strata_core/_import_error monkeypatched: message
  unchanged from before, detail=None).
- present-but-differently-failing direction: strata_core=None with a
  stubbed different ImportError text ("undefined symbol: some_native_fn")
  makes SYS004 report THAT text verbatim, not the generic guess
  (test_sys004_names_real_exception_when_strata_core_fails_differently,
  and verified live against aprog-public the same way -- DesignLoadError
  .detail carried the stubbed exception through to the message).

Consumer-repo validation (read-only, no edits to aprog-public):
- Before understanding the masking site: confirmed via the ticket's own
  report that SYS004 no longer reproduces there today (natives are
  correctly installed after the separate T-2708 install-tool fix) --
  `frob check --only sys .` in aprog-public with the FIXED worktree
  build: 0 SYS004 findings (12 SYS003, 122 SELFAUDIT001, all pre-existing
  and unrelated to this ticket).
- Reproduced both directions of the masking defect directly against
  aprog-public's real design/aprog-public.strata via
  frob.strata._design_load.load_design_ids() with
  frob.strata._parse.strata_core/_import_error monkeypatched -- see
  positive controls above; output captured live in this session.

Filed: none (T-2706 is this agent's second ticket in the same series,
not filed out-of-scope work; the E402/ruff plumbing needed to keep the
guarded try/except recognized by ruff's own exemption was implemented
within this ticket's declared scope, not filed separately).

Gates: `frob check --ticket T-2707 --only affect_drift --only scope
--only coverage --only fmt` clean of any finding anchored at this
ticket's touched files (SCOPE/COV/DRIFT/AFFECT errors present are
repo-wide pre-existing findings in files this ticket never touched, per
the tool's own scope-note: those gate families run unscoped under
--ticket). `uv run ruff check` / `uv run ty check` clean on every touched
file. Full touched-set pytest module run
(test_parse.py/test_facts.py/test_design_load.py/test_gates.py, filtered
to Sys/Parse/Facts/DesignLoad/NativeExtension/StrataCore) is clean except
one pre-existing, unrelated failure
(TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure, a
stale `expect_heterogeneous` monkeypatch signature mismatch in
frob.lang.parse_file, reproduces identically with none of this ticket's
files touched -- confirmed unrelated to _sys.py/_parse.py/_facts.py/
_design_load.py).

Follow-up fixes after the first done-report/check pass:
- COV001 on both strata_core_import_error() (frob:doc anchor added,
  docs/strata/surface.md#parser, new prose there describing the T-2707
  fix).
- AFFECT001 on DesignLoadError/parse_module (resolved by the same doc
  edit -- file-level, not anchor-level, per _affect_ref_file).
- COV002 on 4 new test methods (added frob:ticket T-2707 directives).
- DRIFT002 (all 6): my frob:tests directives used `::` between class and
  method instead of this repo's `.` convention -- fixed in both
  _parse.py and _facts.py.
- PRE001: refreshed via `frob ticket sweep T-2707`.
- ruff E402 (9 findings self-introduced): the two-statement except-body
  (`strata_core = None; _import_error = f"..."`) broke ruff's own
  try/except-guarded-import E402 exemption for every import line below
  it. Fixed with a single tuple-assignment statement in the except body
  plus a post-import `if "_import_error" not in globals(): ...` default
  for the success path (placed after the import block so it cannot
  retrigger the same exemption check).
Re-ran `frob check --ticket T-2707 --only coverage --only affect_drift
--only drift --only prework` after all of the above: zero findings
anchored at any of this ticket's touched files (remaining findings are
all pre-existing/waived, repo-wide, in files outside this ticket's
scope).

### Changed
```
 docs/strata/surface.md          | 20 +++++++++
 src/frob/gates/_sys.py          | 17 +++++++-
 src/frob/strata/_design_load.py | 22 ++++++++--
 src/frob/strata/_facts.py       | 37 +++++++++++++++--
 src/frob/strata/_parse.py       | 43 ++++++++++++++++---
 tests/test_gates.py             | 45 ++++++++++++++++++++
 tests/unit/strata/test_facts.py | 20 +++++++++
 tests/unit/strata/test_parse.py | 58 ++++++++++++++++++++++++++
 tickets/T-2707/done-report.md   | 91 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2707/ticket.md        |  2 +-
 10 files changed, 341 insertions(+), 14 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 45 error(s), 988 warning(s), 681 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
