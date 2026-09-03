## Done report

Measured `frob check --only registry` on main: gate:REG 3 errors, all
REG002, all in docs/design/registry/check-coverage.yaml -- CHK-GATE-
VERSION001/CHK-GATE-TDD001/CHK-GATE-VMOD001, each asserting
"<RULE> is a live, enforced gate rule".

All three rules ARE live and enforced: frob.gates._version_coupling.py
emits VERSION001, frob.gates._tdd_order.py's RULE_TDD001 constant names
TDD001, frob.gates._vmodel.py emits VMOD001 -- all three appear in real
findings on this repo's own gate output. The registry doc was correct;
src/frob/gates/_waive.py's _KNOWN_GATE_RULES frozenset (the known_rules
set REG002 cross-checks handled_by against) was simply missing all
three. Added them, matching the existing PROFILE001/PLATFORM001
entries' comment style and citing each rule's own introducing ticket.

Re-measured: gate:REG 3 -> 0.

Deferred from an earlier attempt (originally bundled into T-3364)
because src/frob/gates/_waive.py carried a live in-progress lease from
T-3295 (an unrelated feature actively reworking the same frozenset
region) at the time -- landed separately now that T-3295 has landed.

Filed as a draft off T-3343 (measurement-first triage ticket for the
wider gate:COV/TICK/REL/REG/REF sprint assignment); mints a real id at
land/renumber.

### Changed
```
 src/frob/gates/_waive.py | 12 ++++++++++++
 tickets/T-3382/ticket.md |  2 ++
 2 files changed, 14 insertions(+)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_skewed_core_version_fires` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestClassifyOrder::test_fires_when_implementation_precedes_test` (pytest node id, verified passing when recorded)
- `tests/test_gates_vmodel.py::TestVmodelGate::test_fires_vmod001_on_construction_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 43 error(s), 3980 warning(s), 879 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC004@docs/commands/check.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/modules/tickets.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3382, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py

### Acceptance amendments
- [0] replace: 'GIVEN VERSION001/TDD001/VMOD001 registered in _KNOWN_GATE_RULES WHEN their producing gates run against a violating fixture THEN each rule fires through the real production invocation (not a mocked/stubbed check)' -> "GIVEN VERSION001/TDD001/VMOD001's own production gate WHEN run against each rule's existing violating fixture THEN the gate fails the fixture (fires the finding) and passes a clean counterpart fixture -- proving each rule fires through the real production invocation, not a mocked/stubbed check" (reason: T-0756: fixture-acceptance grammar requires the criterion text to name both a FAIL and a PASS outcome; logan, 2026-08-29)
