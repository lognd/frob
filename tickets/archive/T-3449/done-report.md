## Done report

Changed: none (no code diff in T-3449's declared scope
src/frob/strata/_selfconform*.py, _claims.py, _facts.py -- see below)

Root cause was NOT in this ticket's scope. Round 2's own failure log already
established there is no wall-time regression between b94cea5d0 and ac5c2ae67
for the two selfaudit001 tests (all four measurements land in a ~2s band),
so no commit in that 30-commit window is bisectable, and it root-caused the
ambient cost driver to src/frob/strata/_effects.py::_via_matches /
_via_matches_site's uncached O(files x globs) fnmatch scan against
design/frob.strata's 250+-entry testsuite via-list -- filed as T-3458,
outside T-3449's file scope.

T-3458 has since landed (3ce02f5c9): a compiled-glob cache for
_via_matches/_via_matches_site. Re-measured post-landing with T-3449
unblocked:

  FROB_SUGGEST_ACK=1 timeout 420 uv run pytest -n 4 -p no:cacheprovider \
    tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations \
    tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001 \
    tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001 \
    tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design \
    tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses

Result: 4 passed, 1 failed, in 171.96s (wall 176s) -- ZERO worker crashes,
ZERO "node down"/"crashed" lines in the log. This is the same order of
magnitude as b94cea5d0's historical 230s for this bundle, and well under
the acceptance bound of "same order of magnitude", resolving anomaly #1's
symptom (the xdist stall/crash) even though its root cause was fixed by
T-3458, not by anything in T-3449's own scope.

The single failure (test_sys_gate_zero_violations) is NOT the stall/crash
this ticket tracks -- it is a real, pre-existing SELFAUDIT001 finding
(8 violations: undeclared fs.write/exec in
tests/unit/strata/test_strata_core_gil.py, added by T-3457's GIL fix, and
undeclared env.read in tests/unit/verify/test_worker.py) that requires
editing design/frob.strata's testsuite via-list -- outside T-3449's scope
(src/frob/strata/_selfconform*.py, _claims.py, _facts.py only). Filed as a
new ticket (draft T-3465) rather than fixed here.

Anomaly #2 (per-test timeout not firing) was already root-caused and fixed
in round 1: strata-core's #[pyfunction]s held the GIL for the whole native
call, starving pytest-timeout's thread-method watchdog; fixed via
py.allow_threads in strata-core/src/lib.rs, landed as T-3457 (92f97987137f),
outside T-3449's Python-file scope as well.

Evidence: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001,
tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001,
tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design,
tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
(all 4 verified passing in the 176s bundled run above; test_sys_gate_zero_violations
excluded from evidence since it fails on the unrelated pre-existing finding, not on
this ticket's stall/crash)

Filed: T-3465 (SELFAUDIT001: testsuite node undeclared fs.write/exec
and env.read, design/frob.strata scope)

Gates: gate:SCOPE/gate:DRIFT/gate:WAIVE findings under `frob check --ticket
T-3449` are all pre-existing repo-wide findings unrelated to this ticket (no
code was touched in T-3449's scope this round) -- see command output;
no frob:waive added since no line of scoped code changed.

### Changed
```
 tickets/T-3449/ticket.md           |  7 ++++++-
 tickets/T-3465/ticket.md | 39 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 45 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 12 error(s), 4229 warning(s), 861 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
