## Done report

tests/gates_suite/test_test_gate.py::TestTestGate.test_ci_workflow_self_gate_does_not_swallow_errors pinned the literal pre-T-4460 'run: uv run frob check\n' line, broken when T-4460 changed the self-gate step to 'set -o pipefail; uv run frob check | tee $RUNNER_TEMP/frob-check.log'. Replaced the literal-line assertion with a structural check via a new module-level _self_gate_run_script_errors helper that still fails on the original || echo ::warning / || true / ; true swallows and adds a new tee-without-pipefail swallow check. TestSelfGateRunScriptSwallowDetection (7 tests) is a positive control proving the detector actually fires on each planted swallow shape (warning-echo, ||true, ;true, tee-without-pipefail, missing invocation) and stays clean on both accepted shapes (bare, teed-with-pipefail) plus the real ci.yml. Full tests/gates_suite/test_test_gate.py run: 119/119 passing. BUG002 waived (confirmatory-only by construction, same shape as T-4430/T-4460 -- the real subject was verified via the positive-control class, not the FAIL-before/PASS-after pairing).

### Changed
```
 tests/gates_suite/test_test_gate.py | 140 ++++++++++++++++++++++++++++++++++--
 tickets/T-4481/ticket.md            |  10 +++
 2 files changed, 144 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/gates_suite/test_test_gate.py::TestTestGate::test_ci_workflow_self_gate_does_not_swallow_errors` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_clean_bare_invocation_has_no_errors` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_clean_teed_invocation_with_pipefail_has_no_errors` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_original_t1265_warning_swallow_is_caught` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_bare_or_true_swallow_is_caught` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_semicolon_true_swallow_is_caught` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_teed_invocation_without_pipefail_is_caught` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_missing_invocation_entirely_is_caught` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestSelfGateRunScriptSwallowDetection::test_real_ci_workflow_self_gate_script_is_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 2 error(s), 4863 warning(s), 967 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md
