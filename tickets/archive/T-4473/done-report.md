## Done report

Changed:
scripts/artifact_smoke.py::_run_doctor_in_scratch_cwd (new, shared helper)
scripts/artifact_smoke.py::check_base_install (now calls the shared helper)
scripts/artifact_smoke.py::check_native_extra (now calls the shared helper, was the bug)

Evidence: tests/unit/test_artifact_smoke_script.py::TestCheckNativeExtra::test_doctor_runs_outside_work_dir_not_process_cwd (frob:tests T-4473; repro'd genuinely failing at 133602733 via --check-repro, then passing after the fix commit). Full tests/unit/test_artifact_smoke_script.py: 24 passed.

Filed: none (no out-of-scope work found; docs/guides/release.md#artifact-smoke-stage-t-3884 needed no text change since it already describes doctor running against the installed artifact -- waived AFFECT001 instead of widening scope, reason recorded in both check_* frob:waive directives).

Gates: uv run frob check --ticket T-4473 -- 3 remaining errors (gate:DRIFT src/frob/doctor.py, gate:REF pre-existing dangling frob:used-by declarations in invariants/ and tickets/T-4196, ruff-format on tests/test_tickets_triage_dates.py) are pre-existing on main, none in scripts/artifact_smoke.py or tests/unit/test_artifact_smoke_script.py -- verified via `git diff main -- <those files>` showing zero diff and doctor.py's content hash identical to main. gate:PRE/gate:SCOPE/gate:AFFECT/gate:COV/gate:FMT (the ticket-scoped gates) all clean after `frob ticket sweep T-4473`.

### Changed
```
 scripts/artifact_smoke.py                | 55 +++++++++++++++++++++++++++++---
 tests/unit/test_artifact_smoke_script.py | 27 ++++++++++++++++
 tickets/T-4473/ticket.md                 |  2 ++
 3 files changed, 79 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_artifact_smoke_script.py::TestCheckNativeExtra::test_doctor_runs_outside_work_dir_not_process_cwd` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4851 warning(s), 971 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md
