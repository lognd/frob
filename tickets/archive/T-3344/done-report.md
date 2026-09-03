## Done report

DRIFT002's ~87 findings were overwhelmingly one root cause -- `frob:tests`
directives written with pytest's collect-only `Class::method` separator instead
of the graph's `Class.method` qualname convention (the exact convention-mismatch
shape T-0265 already documented in `frob.graph.dsl`'s own `_parse_line` comment
as a known false-drift trap, just not previously swept for this occurrence).
Fixed via a scoped regex substitution (`.py::Class` kept, `::method` -> `.method`)
across 12 affected files, verified against each flagged finding's line number
before applying.

The remaining 9 DRIFT findings were two genuine causes: 4 DRIFT001 acks whose
cited doc sections were re-verified against current function bodies and still
match (re-acked: scripts/fleet_status.py::worktrees_touching_ticket,
src/frob/doctor.py::run_diagnosis,
src/frob/tickets/_land_squash.py::_squash_and_splice_ledger_v2), and 5 DRIFT002
doc references in docs/modules/gates.md pointing at symbols that genuinely moved
(Severity/WaiverRef/Violation from src/frob/gates/_models.py to
src/frob/findings.py; evidence_covers_scope from src/frob/gates/__init__.py to
src/frob/tickets/_scope_coverage.py -- retargeted to their real module).

Evidence: 10 pytest node ids bound, one per touched file/directive-cluster; ran
together as `uv run pytest -q tests/unit/test_close_blocked_by_guard.py
tests/unit/test_logging_module.py tests/unit/test_reopen_ticket.py
tests/unit/test_doctor_runner_t1276.py tests/unit/test_app_runners_batch6.py
tests/unit/test_check.py tests/test_ghio.py tests/test_ci_report.py
tests/gates/test_comment_placement.py tests/gates/test_docstring_archaeology.py`
-- 299 passed, 0 failed.

Filed: none -- every finding in gate:DRIFT's scope was addressed directly. The
residual gate:WAIVE (WAIVE011, ratchet lock abandoned) and gate:DOC (DOC002 in
src/frob/tickets/_leases.py, a file this ticket never touched) errors surfaced
by `frob check --ticket T-3344` pre-existed this ticket and are out of scope for
gate:DRIFT.

Gates: `frob check --only drift` (repo-wide) 0 errors, down from 53 measured
pre-work; `frob check --ticket T-3344 --only scope` clean (0 errors, after
adding frob.lock to scope for the frob-ack writes).

### Changed
```
 docs/modules/gates.md                     |  10 +--
 frob.lock                                 |  62 +++++++++++++-
 src/frob/app/check_runner.py              |   4 +-
 src/frob/app/doctor_runner.py             |   4 +-
 src/frob/ci_report.py                     |   4 +-
 src/frob/gates/_comment_placement.py      |  18 ++--
 src/frob/gates/_docstring_archaeology.py  |  10 +--
 src/frob/ghio.py                          |   4 +-
 tests/unit/test_app_runners_batch6.py     |   4 +-
 tests/unit/test_check.py                  |   6 +-
 tests/unit/test_close_blocked_by_guard.py |  12 +--
 tests/unit/test_doctor_runner_t1276.py    |   4 +-
 tests/unit/test_logging_module.py         |  12 +--
 tests/unit/test_reopen_ticket.py          |   6 +-
 tickets/T-3344/ticket.md                  | 137 +++++++++++++++++++++++++++++-
 15 files changed, 243 insertions(+), 54 deletions(-)
```

### Evidence
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_open_blocker_names_the_open_ticket_not_the_terminal_one` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_log_record_reported_via_exactly_one_channel_under_pytest` (pytest node id, verified passing when recorded)
- `tests/unit/test_reopen_ticket.py::TestReopenTicket::test_reopen_requires_done` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_plain_prints_all_available_and_does_not_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_none_progress_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCollectResultsProgressCallback::test_no_callback_matches_pre_t2978_behavior_exactly` (pytest node id, verified passing when recorded)
- `tests/test_ghio.py::TestPreflight::test_no_gh_no_auth_no_remote_never_crashes` (pytest node id, verified passing when recorded)
- `tests/test_ci_report.py::TestParsePytestLog::test_truncated_with_no_evidence_is_not_recoverable` (pytest node id, verified passing when recorded)
- `tests/gates/test_comment_placement.py::TestCplace001::test_must_fire_long_waive_reason` (pytest node id, verified passing when recorded)
- `tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 49 error(s), 5028 warning(s), 884 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC011@docs/guides/release.md, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
