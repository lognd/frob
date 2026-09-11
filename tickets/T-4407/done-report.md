## Done report

Changed: src/frob/app/verify_runner.py (874 -> 715 lines), src/frob/app/_verify_coverage_lock.py (new, T-4041 coverage-lock auto-commit helpers), src/frob/app/_verify_rapid_debt.py (new, T-4324 rapid-debt-visibility helpers), tests/unit/verify/test_verify_runner.py (import paths updated to new modules), docs/modules/verify-rapid-debt-visibility.md (frob:describes anchor + prose updated to new module path). Why: verify_runner.py was 874 lines, over the LARGE001 800-line threshold, and would red the next ubuntu self-gate. Extracted two cohesive, previously-self-contained helper groups (coverage-lock auto-commit T-4041, rapid-debt visibility T-4324) into their own private modules with no behavior change -- same functions, same bodies, only import location moved; verify_runner.py imports both symbols back so call sites are unchanged. Evidence: all 20 tests in tests/unit/verify/test_verify_runner.py pass (pytest -q, exitstatus=0). frob check --ticket T-4407 run chunked (gates-fast, gates-native, gates-security, lint, static) shows 0 errors introduced by this change; the pre-existing repo-wide baseline (19 errors, ruff-format/ty warnings, frob-exports notices) is unrelated to the touched files. Filed: none. Gates: frob check --ticket T-4407 clean of new findings.

### Changed
```
 docs/modules/verify-rapid-debt-visibility.md |   5 +-
 src/frob/app/_verify_coverage_lock.py        |  82 ++++++++++++++
 src/frob/app/_verify_rapid_debt.py           | 102 +++++++++++++++++
 src/frob/app/verify_runner.py                | 163 +--------------------------
 tests/unit/verify/test_verify_runner.py      |  12 +-
 tickets/T-4407/ticket.md                     |   4 +
 6 files changed, 200 insertions(+), 168 deletions(-)
```

### Evidence
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_no_baseline_is_live` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_later_baseline_clears` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_uncovered_stays_live` (pytest node id, verified passing when recorded)
