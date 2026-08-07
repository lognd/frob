## Done report

Zero-config native strata selection: new src/frob/strata/_native_test.py::
run_native_sys_audit composes the SAME shipped checks frob sys audit runs
(load_design_ids -> merge_models -> evaluate_exhaustiveness ->
check_self_conformance) in-process, no duplicated detection. src/frob/
testing/_runners.py special-cases language=="strata" BEFORE runners_by_lang,
so a touched .strata file audits with an empty runners tuple instead of
raising NoRunner. The frob.strata import is DEFERRED inside the function --
a module-level import closes a real cycle (frob.testing -> frob.strata ->
frob.vet -> frob.gates -> frob.testing), reviewer-confirmed via frob-cycle.
A failing strata audit folds to exit_code=1 -> the test run fails (not
silently passed), via TestingError.NativeAuditFailed.

Evidence (3 tests, pass): no-runner-config-needed, empty-model-neutral-pass,
and bad-design-file-fails (asserts result.is_err == NativeAuditFailed, a
genuine failure assertion, not just no-crash).

Coordinator landing fix: the reviewer REJECTED on one unwaived DRIFT002 --
the frob:tests directive at test_testing.py:582 named a nonexistent method
(test_bad_design_file_is_native_audit_failed) while the real method is
test_bad_design_file_fails. Fixed the directive to the real name; malformed=0
and DRIFT002 cleared. Everything else the reviewer verified clean (chain
reuse, deferred-import cycle-break, failure propagation, doc anchors, scope).
Landed via 3-way + new-file create.
