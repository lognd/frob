## Done report

The Windows CI leg is green and its advisory flag is gone. CI run 34758499278 (head 020d2db1f, 2026-09-13) passed all three legs: the Windows Test step 13962/13962 with a 0-error self-gate, after the drain landed 2026-09-12/13 (T-4404 T-4430 T-4442 T-4446 T-4447 T-4450 T-4455 T-4456 T-4457 T-4461 T-4462 plus T-4429/T-4408 earlier). T-3512 (ab7ae6b24) removed continue-on-error from the windows-latest leg and updated tests/unit/test_release_workflow_gate.py and the release/windows-portability docs. T-4142 (the surviving-failures list) was dropped as superseded by the same run. Owner condition for the alpha (no PyPI release until Windows passes and the flag is removed) is met; 0.531.0 cut follows.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 4805 warning(s), 963 waived
- error-findings: REF002@docs/design/macos-portability.md
