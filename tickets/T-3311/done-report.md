## Done report

Re-verified this ticket's premise before landing (Series EN resuming from
Series EC): all three divergent pytest-spawn conventions were confirmed
still live on current main (sys.executable -m pytest in
gates/_bug_repro.py, uv run pytest in app/ticket_runner/_verify.py, bare
pytest PATH lookup in refactor/_verify.py) despite everything that
landed since this branch paused, including T-3305. Checked specifically
for overlap between T-3305's _venv_python_has_frob_importable (probes
whether frob imports through a candidate venv, used by
_python_for_tree to pick which interpreter runs frob check) and this
ticket's pytest_importable (probes whether pytest imports through an
already-resolved interpreter, used by resolve_pytest_argv before
handing back a spawn argv): different tool being probed, different call
shape, no duplication.

perf/_profile.py was in this ticket's original declared scope (T-3268's
own fix target) but T-3268 landed its own sys.executable conversion for
that file independently while this branch was paused -- it needed no
further change here, so it carries no diff despite remaining in scope.

Rebased onto current main: two mechanical merge conflicts (ticket-ledger
scope list, and an insertion-point conflict between two independently
added doc sections in docs/modules/process.md) -- resolved by keeping
both sides, no code conflicts. Re-added docs/modules/process.md to
scope (previously dropped to unblock T-3295's file lease while paused,
per that commit's own recorded note to re-add on resume) and added
tests/unit/test_pytest_spawn.py and docs/commands/refactor.md
(AFFECT001: verify_pytest_collect's argv-build now routes through
resolve_pytest_argv, its doc anchor needed updating).

frob test --base main and a direct pytest run of the 27 relevant tests
(test_pytest_spawn.py, test_pytest_spawn_env_wiring.py, test_refactor.py
TestVerify, test_ticket_runner_pytest_env.py) both passed clean.

frob check --ticket T-3311: gate:SCOPE 0 errors, gate:PREWORK clean,
gate:AFFECT clean, gate:COV 0 errors, gate:FMT 0 errors -- all the
ticket-scoped gates. Every other gate family in that run is repo-wide
per the run's own gate:scope-note; spot-checked gate:DOC and gate:DRIFT
findings and confirmed all cite files/symbols outside this ticket's
scope, pre-existing repo debt not introduced here. frob verify status:
quarantine clear.

No out-of-scope work discovered; no new tickets filed.

### Changed
```
 design/frob.strata                    |   8 ++
 docs/commands/refactor.md             |   7 +-
 docs/modules/process.md               |  44 +++++++++++
 src/frob/app/ticket_runner/_verify.py |  45 +++++++++--
 src/frob/gates/_bug_repro.py          |  13 +++-
 src/frob/process/__init__.py          |   8 ++
 src/frob/process/_pytest_spawn.py     | 138 ++++++++++++++++++++++++++++++++++
 src/frob/refactor/_verify.py          |  52 +++++++++----
 tests/unit/test_pytest_spawn.py       |  78 +++++++++++++++++++
 tickets/T-3311/ticket.md              |  39 ++++++++++
 10 files changed, 409 insertions(+), 23 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 58 error(s), 4466 warning(s), 880 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_verify.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC003@docs/commands/sys.md, DOC004@docs/commands/check.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/modules/tickets.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3311, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
