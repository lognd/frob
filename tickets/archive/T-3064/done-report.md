## Done report

T-3064 is BLOCKED, not implemented. The extraction was not performed
against my own judgement to hand-edit imports.

WHAT I RAN:
  timeout 540 uv run frob refactor split frob.gates._models \
    --symbols Severity,WaiverRef,DebtEntry,Violation \
    --into frob.gates._findings

RESULT: refused at the `import_resolution` verify stage with ~40 false
"unresolved: ... shares its physical line with another statement
(semicolon-joined)" findings, e.g.:
  src/frob/gates/decisions.py:109 (plain function-local
    `from frob.gates._models import Severity, Violation`, no sibling
    statement present -- confirmed with `cat -A`)
  src/frob/gates/_coverage_sites.py:81 (`if TYPE_CHECKING:`-guarded import)
No files were changed on disk; the operation rolled back cleanly
(`git status --porcelain` empty afterward).

ROOT CAUSE (traced, not guessed): `_shares_line_with_sibling_statement()`
in `src/frob/refactor/_scan.py:57` uses `ast.walk(tree)` to find a
"sibling" statement sharing the import's physical line. `ast.walk` also
yields every ANCESTOR compound statement (the enclosing `FunctionDef`,
`If`, `Try`, ...), whose own line span always overlaps its body's import
-- so the check misfires on the import's own enclosing scope, not a real
semicolon-joined sibling. It also matches on `.module` alone, so an
untouched symbol's (`GateError`/`GateReport`/`GateStats`) nested import
anywhere in the repo is enough to gate a move of `Severity`/`Violation`/
`WaiverRef`/`DebtEntry`, which is a separate defect (should filter by the
actually-moved names).

I did not attempt `move-module` as a workaround -- it shares
`src/frob/refactor/_scan.py`'s reference scan, so it would hit the
identical false refusal on any of the same nested imports.

Filed: T-3066, "frob refactor split/move-module false-refuses
on any nested import of the source module" (bug, scope
src/frob/refactor/_scan.py), with full root-cause trace and a repro. This
land is the mechanism by which that draft gets its real ticket id on
main (per T-2197: a promoted/created id inside a worktree is invisible to
the fleet until the worktree lands).

T-3064 blocked_by=[T-3066] via `frob ticket block`. No code
change to verify with tests -- nothing outside `tickets/` was touched.
`frob cycle` before/after was NOT re-measured since no extraction
happened; the 182-node baseline from the ticket body stands unchanged.

Next cut: not filed -- this ticket never reached the re-measurement step
the plan calls for. Once T-3066's real id lands a fix, T-3064
should be unblocked and retried with the same `frob refactor split`
command above.

Changed: none (tickets/ only)
Evidence: tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite
  (the existing correctly-detected POSITIVE case for the exact detector
  whose false-positive misfire blocked this ticket; passes unchanged,
  confirming the detector's true-positive path still works and the
  refusal T-3064 hit is the false-positive path traced in T-3066)
Filed: T-3066 (bug, tooling gap in frob.refactor._scan)
Gates: not run -- no src/ change in this ticket's own diff

### Changed
```
 tickets/T-3064/done-report.md      | 70 ++++++++++++++++++++++++++++++++
 tickets/T-3064/ticket.md           |  6 ++-
 tickets/T-3066/ticket.md | 83 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 158 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 60 error(s), 1109 warning(s), 858 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3063/ticket.md, DOC006@tickets/T-3064/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
