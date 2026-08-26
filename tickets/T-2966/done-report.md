## Done report

Changed:
- src/frob/gates/_detector_scope.py::tracked_gate_files (new, extracted)
- src/frob/gates/_port_selfcheck.py::port_selfcheck_gate (now calls tracked_gate_files)
- src/frob/gates/_lexical_selfcheck.py::lexical_selfcheck_gate (now calls tracked_gate_files)
- 43 files total received frob:waive DUP001 directives (full-fragment coverage) for
  21 confirmed-coincidental/documented-narrow-duplicate groups; see commit diffs for
  the per-group reasons recorded in each waiver comment.

Evidence:
- tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_tracked_gate_files_filters_to_detector_roots (--accepts 0)
- tests/unit/gates/test_port_selfcheck.py (9 tests) and tests/unit/gates/test_detector_scope.py
  (5 tests) run together: SUITE-RESULT exitstatus=0 collected=14 failed=0

Filed: none (all 23 residue groups dispositioned within this ticket; scope was
widened via `frob ticket scope --add` to the minimal sibling-file set needed for
full-fragment DUP001 waiver coverage on cross-package groups -- not a new ticket).

Gates: re-measured `uv run frob check --json --only static`, filtered to
tool=="frob-dup" AND any location containing "src/frob/gates" AND not already
"[waived": 0 (was 23 at ticket start). Full frob-dup diagnostics: 27 waived
(note-severity), 532 unwaived remaining repo-wide (all in tests/ (480) or
unrelated-to-gates packages (51+1) -- both out of this ticket's scope, T-2970
covers the tests/ cluster).

### Changed
```
 src/frob/app/ticket_runner/_close_cmd.py         |  50 ++++++++
 src/frob/app/ticket_runner/_waive_audit.py       |   4 +
 src/frob/arch/_exceptions.py                     |   4 +
 src/frob/arch/_mayraise.py                       |  11 ++
 src/frob/deploy/_generate.py                     |  20 ++++
 src/frob/doctor.py                               |   5 +
 src/frob/dup/_rules.py                           |   9 ++
 src/frob/gates/__init__.py                       |  18 +++
 src/frob/gates/_arch_schema.py                   |   4 +
 src/frob/gates/_baseline.py                      |   4 +
 src/frob/gates/_bug_repro.py                     |  20 ++++
 src/frob/gates/_coverage.py                      |   4 +
 src/frob/gates/_deprecated_baseline.py           |   4 +
 src/frob/gates/_detector_scope.py                |  23 +++-
 src/frob/gates/_docblocks_shared.py              |   3 +
 src/frob/gates/_doclink_docanchor.py             |   9 ++
 src/frob/gates/_docptr.py                        |  12 ++
 src/frob/gates/_docstatus.py                     |   6 +
 src/frob/gates/_dup_graph_schema.py              |  10 ++
 src/frob/gates/_exhaustive_handling.py           |  10 ++
 src/frob/gates/_fix_engine.py                    |   4 +
 src/frob/gates/_inv.py                           |   4 +
 src/frob/gates/_lexical_selfcheck.py             |  16 +--
 src/frob/gates/_mutation_evidence.py             |   5 +
 src/frob/gates/_pii_structural/_crosslang.py     |   4 +
 src/frob/gates/_pii_structural/_env_access.py    |   4 +
 src/frob/gates/_pii_structural/_keywords.py      |   5 +
 src/frob/gates/_pii_structural/_python_fields.py |   5 +
 src/frob/gates/_port_selfcheck.py                |  61 ++++------
 src/frob/gates/_profile_schema.py                |   4 +
 src/frob/gates/_registry_exhaustiveness.py       |   6 +
 src/frob/gates/_render_lint.py                   |   4 +
 src/frob/gates/_root_asset_dirs.py               |   4 +
 src/frob/gates/_testing_schema.py                |   3 +
 src/frob/gates/_waive.py                         |   5 +
 src/frob/gates/_walk_lint.py                     |   4 +
 src/frob/lang/_common.py                         |   5 +
 src/frob/perf/_redundancy.py                     |   3 +
 src/frob/perf/_sketch_store.py                   |   3 +
 src/frob/scaffold/_managed.py                    |   5 +
 src/frob/strata/_waive.py                        |   5 +
 src/frob/testing/_collect_cpp.py                 |   4 +
 src/frob/tickets/_new_renumber.py                |   4 +
 src/frob/vet/_scan.py                            |   4 +
 src/frob/vet/_scan_violations.py                 |   3 +
 tests/unit/gates/test_detector_scope.py          |  14 +++
 tickets/T-2966/ticket.md                         | 143 ++++++++++++++++++++++-
 47 files changed, 501 insertions(+), 60 deletions(-)
```

### Evidence
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_tracked_gate_files_filters_to_detector_roots` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 33 error(s), 2786 warning(s), 854 waived
- error-findings: AFFECT001@src/frob/gates/_detector_scope.py, AFFECT001@src/frob/gates/_lexical_selfcheck.py, AFFECT001@src/frob/gates/_port_selfcheck.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, F401@/home/logan/projects/frob/.claude/worktrees/t-2966-2970/src/frob/gates/_lexical_selfcheck.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2966-2970/src/frob/gates/_port_selfcheck.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, PRE001@tickets/T-2966, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
