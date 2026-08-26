## Done report

Changed:
- src/frob/ghio.py (new)
- tests/test_ghio.py (new)
- docs/modules/ghio.md (new)

Evidence:
- tests/test_ghio.py::TestPreflight::test_success
- tests/test_ghio.py::TestJobLog::test_empty_log_for_a_failed_job_is_named
- tests/test_ghio.py::TestJobLog::test_truncated_log_for_cancelled_run
- tests/test_ghio.py::TestPreflight::test_no_gh_no_auth_no_remote_never_crashes
- tests/test_ghio.py::TestPreflightIntegration::test_real_subprocess_seam_against_a_fake_gh_binary
- (20 total tests in tests/test_ghio.py cover every named GhError mode)

Filed: none

Gates: frob check --ticket T-2983 (docblocks/coverage/test/scope/archgate/
dead_symbols/doclink/docanchor families) clean for ghio.py, test_ghio.py,
docs/modules/ghio.md -- 20 pre-existing repo-wide errors unrelated to this
change remain (baseline, unaffected by this ticket).

### Changed
```
 docs/modules/ghio.md     | 124 +++++++++++++
 src/frob/ghio.py         | 458 +++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_ghio.py       | 441 +++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2983/ticket.md |  59 ++++++
 4 files changed, 1082 insertions(+)
```

### Evidence
- `tests/test_ghio.py::TestPreflight::test_success` (pytest node id, verified passing when recorded)
- `tests/test_ghio.py::TestJobLog::test_empty_log_for_a_failed_job_is_named` (pytest node id, verified passing when recorded)
- `tests/test_ghio.py::TestJobLog::test_truncated_log_for_cancelled_run` (pytest node id, verified passing when recorded)
- `tests/test_ghio.py::TestPreflight::test_no_gh_no_auth_no_remote_never_crashes` (pytest node id, verified passing when recorded)
- `tests/test_ghio.py::TestPreflightIntegration::test_real_subprocess_seam_against_a_fake_gh_binary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 26 error(s), 479 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, REF002@docs/modules/ghio.md, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, WIRE001@src/frob/ghio.py
