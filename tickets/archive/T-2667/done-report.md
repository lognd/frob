## Done report

Owner decision executed (accounting-now, decomposition-later):

Changed:
src/frob/__init__.py (module-level comment block, T-2363's CYCLE001
declaration) -- converted the inert "frob:waive CYCLE001" prose
declaration into a real, parsed `frob:debt CYCLE001 reason="..."
ticket="T-3350"` directive; corrected the stated premise to
the T-2667-measured picture (candidate 2 landed, SCC did not collapse,
still 160 nodes closed by 5 edges, 1 top-level + 4 function-local).

Filed: T-3350 "Decompose the serve/tickets/testing/app
CYCLE001 SCC (160 nodes, post-1.0.0)" -- carries T-2667's corrected
edge analysis and the import-time-vs-SCC-measurement distinction
forward as the post-1.0.0 epic. tier=epic, priority=low.

Evidence: verified via `frob check --only static` that the new
`frob:debt CYCLE001 ... ticket="T-3350"` directive parses
cleanly (no DEBT001 malformed-directive, no DEBT002 missing/closed-
ticket finding) and that CYCLE001 at src/frob/__init__.py remains
exactly as live an error as it was before this change (frob:debt does
not discharge a gate finding, only frob:waive does, per
frob.gates._waive._apply_waivers only indexing EdgeKind.WAIVE -- this
ticket is accounting-only, not a suppression, matching the owner's
"the rule DOES apply... that is debt, not a waiver" framing). No new
CYCLE001 error introduced; no regression.

Gates: `frob check --ticket T-2667 --only gates-fast` run (FROB_AGENT
refuses a full/unchunked pass, T-0627) -- all FAIL counts on gate
families outside SCOPE/PREWORK are repo-wide baselines unrelated to
this ticket's two-file change (confirmed against the tool's own NOTE:
those counts are not scoped to this ticket). The one SCOPE001 hit
(tickets/T-3350/ticket.md outside declared scope) is this
ticket filing its own required follow-up ticket; a scope --add for it
was blocked by a live cross-worktree lease on tickets/** (T-3338,
T-1868) at close time -- filing a follow-up ticket while working
another is expected/routine and not itself a behavioral defect.

This ticket makes no runtime behavior change (comment-only edit to
src/frob/__init__.py, plus filing a ticket) -- closed via
--no-behavior-change.

### Changed
```
 src/frob/__init__.py          | 47 ++++++++++++++---------
 tickets/T-2667/done-report.md | 59 ++++++++++++++++++++++++++++
 tickets/T-2667/ticket.md      | 24 +++++++++++-
 tickets/T-3350/ticket.md      | 89 +++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 201 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDebtGate::test_debt002_open_ticket_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 77 error(s), 3989 warning(s), 883 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOC011@docs/guides/release.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
