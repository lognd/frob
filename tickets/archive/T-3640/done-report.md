## Done report

Repointed 9 self-referential frob:tests directives in tests/unit/arch_suite/test_complexity.py (3) and test_misc.py (6) -- each moved test's own self-citation still pointed at the pre-split tests/unit/test_arch.py path (same bug class T-3635 just fixed for T-3591). Verified: frob check --only drift shows 0 DRIFT002; ruff check clean on both files; pytest on both files 42/42 green.

### Changed
```
 tests/unit/arch_suite/test_complexity.py |  6 +++---
 tests/unit/arch_suite/test_misc.py       | 12 ++++++------
 tickets/T-3640/ticket.md                 | 16 ++++++++++++++--
 3 files changed, 23 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt::test_reasoned_exempt_suppresses_finding` (pytest node id, verified passing when recorded)
- `tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 10 error(s), 4216 warning(s), 896 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
