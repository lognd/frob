## Done report

Changed:
  src/frob/scaffold/project.py (wrapped 4 over-88-char E501 lines: the 3 named in
    the ticket at lines 115/248/683, plus 1 additional pre-existing over-88-char
    docstring line at line 709 found while fixing the same file)
  tests/unit/test_scaffold_project_e501_t2596.py (new repro test)

Evidence:
  tests/unit/test_scaffold_project_e501_t2596.py::TestScaffoldProjectLineLength::test_no_unexempted_long_lines
    (designated repro, FAILED_AT_PARENT verified against 7c5af59b8)

Filed: none

Gates: frob check --only lint --ticket T-2596: 0 E501 findings in
src/frob/scaffold/project.py (verified directly, previously 1 finding at old
line 709/now-712). frob check --only scope --ticket T-2596: 0 SCOPE errors
(3 pre-existing repo-wide DRIFT001/CLAUDE001 errors unrelated to this
ticket's scope).

Not fixed, disclosed per ticket instructions: src/frob/app/ticket_runner/_ledger_mirror.py
still carries an over-88-char line (now at line 366, content has moved since the
ticket was filed -- it was line 72 at filing time). This file is under T-2587's
scope per the ticket's own note; T-2587 landed during this series (commit
ed6f57271) but did not touch this line, so the E501 there is still live. Out of
this ticket's declared scope (src/frob/scaffold/project.py only) -- not touched,
per the coordinator's explicit instruction to route it separately.

### Changed
```
 src/frob/scaffold/project.py                   | 18 ++++++++-----
 tests/unit/test_scaffold_project_e501_t2596.py | 37 ++++++++++++++++++++++++++
 tickets/T-2596/ticket.md                       | 13 ++++++++-
 3 files changed, 60 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_project_e501_t2596.py::TestScaffoldProjectLineLength::test_no_unexempted_long_lines` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/scaffold/project.py, ARCH102@src/frob/tickets/_doable.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2596, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
