## Done report

NOTE ON DISPATCH ID: this session was briefed as "T-2967 -- the 3
remaining exit-code-contract mismatches in tests/system/test_cli_cycle.py",
but T-2967's actual ticket content is a different, unrelated defect
(macOS AF_UNIX sun_path length limit in frob.serve._socketd, 12
failures in tests/test_app_daemon_proxy.py). The ticket matching the
briefed description -- test_cli_cycle.py's exit-code-contract
mismatches -- is T-2968. `frob ticket start T-2967` was run, immediately
recognized as the wrong content, and `frob ticket fail T-2967 --summary
...` was run to return it to queue untouched (no scope files edited).
This report is for T-2968, the ticket whose content matches the brief.

Root cause: `frob.app.cycle_runner.run`'s own docstring documents the
CLI contract explicitly -- "exits 1 (not 0) when real cycles are found".
`tests/system/test_cli_cycle.py::test_cycle_exit_zero`,
`test_deep_cycle_exit_zero`, and `test_suggest_cycle_exit_zero` all
asserted `returncode == 0` against `cycle_dir`/`deep_cycle_dir` fixtures
that DELIBERATELY construct a real import cycle -- contradicting the
runner's own documented contract, not the other way around. The CODE
was right; the TESTS were wrong. Fixed by updating the three assertions
to `returncode == 1` and renaming the three tests
(`test_cycle_exit_one`, `test_deep_cycle_exit_one`,
`test_suggest_cycle_exit_one`) so the name states the actual, correct
expectation -- matching the ticket's own acceptance wording ("or
renamed/reworked if their intent was actually to assert something
else").

Baseline (before fix): 9/12 passed, 3/12 failed --
test_cycle_exit_zero, test_deep_cycle_exit_zero,
test_suggest_cycle_exit_zero, each `assert 1 == 0`.

After fix: 12/12 pass.

Changed: tests/system/test_cli_cycle.py
  - test_cycle_exit_zero -> test_cycle_exit_one, asserts returncode == 1
  - test_deep_cycle_exit_zero -> test_deep_cycle_exit_one, asserts
    returncode == 1
  - test_suggest_cycle_exit_zero -> test_suggest_cycle_exit_one, asserts
    returncode == 1
No production code changed -- the contract in cycle_runner.run was
already correct and is left untouched.

Evidence: tests/system/test_cli_cycle.py::test_cycle_exit_one,
tests/system/test_cli_cycle.py::test_deep_cycle_exit_one,
tests/system/test_cli_cycle.py::test_suggest_cycle_exit_one (all three
bound to acceptance indices 0-4). Full file re-run: 12/12 pass
(SUITE-RESULT: exitstatus=0 collected=12 failed=0).
Filed: none -- no out-of-scope discovery beyond the T-2967 id-mismatch
already disclosed above (T-2967 itself is untouched and back in queue,
its own content is unrelated pre-existing ticket work, not something
this ticket needed to file).
Gates: no new public symbol added; test-only rename+fix, no COV001/
TEST001 surface. frob:tests/frob:doc directives not applicable.

### Changed
```
 tickets/T-2967/ticket.md |  3 +++
 tickets/T-2968/ticket.md | 31 +++++++++++++++++++++++++------
 2 files changed, 28 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/system/test_cli_cycle.py::test_cycle_exit_one` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_cycle.py::test_deep_cycle_exit_one` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_cycle.py::test_suggest_cycle_exit_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 28 error(s), 472 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, PRE001@tickets/T-2968, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
