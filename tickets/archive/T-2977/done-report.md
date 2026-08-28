## Done report

Changed:
- src/frob/gates/_lexical_selfcheck.py (dropped unused is_detector_package_file import)
- src/frob/gates/_port_selfcheck.py (dropped unused is_detector_package_file import)

Both files kept importing `is_detector_package_file` after T-2966's
`tracked_gate_files` extraction moved its only call site into
`_detector_scope.py`, leaving the name unused (F401) in each -- the
regression this ticket was auto-filed against.

Evidence:
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged
- tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_tracked_gate_files_filters_to_detector_roots

Filed: none.

Gates: F401 no longer fires on either file (import removed); both test
files above collected and passed (14/14, exitstatus=0) after the fix.

### Changed
```
 src/frob/gates/_lexical_selfcheck.py | 6 +-----
 src/frob/gates/_port_selfcheck.py    | 6 +-----
 tickets/T-2977/ticket.md             | 8 +++++++-
 3 files changed, 9 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_tracked_gate_files_filters_to_detector_roots` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 27 error(s), 489 warning(s), 856 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
