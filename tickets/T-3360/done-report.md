## Done report

Same-day regression from T-3266 (commit 886eec895, landed ~22:35 on
2026-08-28). T-3266 wired `_stale_claims_reason` (docs/refs a MEASURED
206-of-1934 defect) into `_done_transition_structural_guard`, which is
shared by BOTH `transition()`/`close` and `reverify_close_guard` via
`_done_transition_guard`.

Confirmed the guard's design conflict directly: `close` requires the
operator to have already run `frob ticket done-report` before closing
(the Done report is expected to be current when the write happens), so
the T-3266 check is correct there. `reverify` is the opposite shape by
design (churn item 6, docs/audits/coordination-churn.md): its caller
(`frob.app.ticket_runner._reverify`) accepts NEW evidence via
`--evidence`/`--evidence-cmd` and only refreshes the Done report's
Captured-claims section AFTER the full guard suite passes
(`recover_done_report_why` + `set_done_report`). Because
`reverify_close_guard` reused the unconditional T-3266 check, the guard
always saw the PRE-refresh claims count against the NEW evidence count
and refused -- reverify could never succeed when evidence was added,
which is the only scenario reverify exists for. Reproduced solo and
under load:
`tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged`
failed deterministically with `StaleClaimsInDoneReport` on current main
before this fix.

Fix: threaded a `skip_stale_claims: bool = False` parameter through
`_done_transition_guard` -> `_done_transition_structural_guard`.
`reverify_close_guard` is the only caller that passes `True`; `close`
(via `transition`) is unaffected and still refuses on a genuinely stale
claims count. Extracted the T-3266 check itself into a small
`_stale_claims_guard` helper to keep `_done_transition_structural_guard`
at the ARCH001 60-line threshold after the added parameter/docstring.
Updated `docs/modules/tickets.md`'s Public API section (AFFECT001:
`reverify_close_guard`'s affects()-closure doc) to document the new
parameter and why it exists.

Verified close's own T-3266 protection is untouched: all 4
`tests/test_tickets.py::TestStaleClaimsGuard::*` tests still pass
unmodified.

## Done report

Changed:
src/frob/tickets/_evidence.py::_done_transition_guard
src/frob/tickets/_evidence.py::_done_transition_structural_guard
src/frob/tickets/_evidence.py::_stale_claims_guard
src/frob/tickets/_evidence.py::reverify_close_guard
docs/modules/tickets.md#public-api

Evidence:
tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged (1 passed, was the failing repro)
tests/test_tickets.py::TestStaleClaimsGuard::test_zero_claims_with_real_evidence_refused (1 passed, close-path regression guard)
tests/test_tickets.py::TestStaleClaimsGuard::test_wrong_nonzero_claims_refused (1 passed, close-path regression guard)
tests/test_tickets.py::TestStaleClaimsGuard::test_matching_claims_not_flagged (1 passed, close-path regression guard)
tests/test_tickets.py::TestStaleClaimsGuard::test_no_claims_section_not_flagged (1 passed, close-path regression guard)
Also ran clean (not bound as evidence, broader sanity): tests/test_ticket_reverify.py (9/9), tests/test_tickets.py minus TestArchive (197/197), tests/test_tickets_cmd_evidence.py + tests/test_ticket_evidence.py (56/56).

Filed: none (this ticket itself is the same-day-regression filing the coordinator asked for)

Gates: frob check --ticket T-3360: gate:SCOPE clean (0 errors,
187 warnings -- pre-existing breadth noise from docs/modules/tickets.md's
shared #public-api anchor, not introduced by this diff), gate:AFFECT
clean (no finding this run, was 1 before the doc edit), gate:ARCH clean
on the touched functions (`_done_transition_structural_guard` sits
exactly at the 60-line threshold, unflagged; `_stale_claims_guard` new
at 14 lines). ruff-format clean on both touched files (docs/modules
markdown formatting is experimental/skipped by ruff itself, not a repo
convention here). Full unscoped `frob check` was not completed cleanly
this session -- it times out under current host load (23+ concurrent
worktrees, T-3247's known contention) well past the 540s foreground cap
on every attempt; ran targeted `--only` gate families instead
(archgate, arch_schema, affect_drift, scope, coverage, fmt) covering
every family relevant to this diff, all clean or unchanged from
pre-existing repo-wide baseline.

### Changed
```
 docs/modules/tickets.md                 | 11 ++++
 src/frob/tickets/_evidence.py           | 43 +++++++++++----
 tickets/T-3360/done-report.md | 93 +++++++++++++++++++++++++++++++++
 tickets/T-3360/ticket.md      | 49 +++++++++++++++++
 4 files changed, 186 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_zero_claims_with_real_evidence_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_wrong_nonzero_claims_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_matching_claims_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_no_claims_section_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 78 error(s), 4117 warning(s), 886 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOC011@docs/guides/release.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3360, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
