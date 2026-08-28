## Done report

`.claude-scratch/T-3122-close-guard-repro-capture.md` was the SOLE
tracked file under `.claude-scratch/` (confirmed via `git ls-files |
grep -iE "scratch|\.patch$|repro-capture"` -- the two other named
candidates, t-2356-scratch-golden-check.py and t1768.patch under the
worktrees dir, are not tracked at all, and `.claude/worktrees/` is
already git-ignored). Count of other tracked agent-scratch paths found:
ZERO.

Verified nothing cites it as evidence before removing (per the ticket's
own instruction): all references were the REF001 finding string itself,
not a citation, and T-3122 (its origin ticket) is already `done`.

FIX: `git rm --cached` the file, added `.claude-scratch/` to
`.gitignore` (next to the existing `.frob/`/`FROBLEMS.md` local-state
entries). REF001 measured before (fired at ERROR on this path, per the
39 done-report mentions the ticket names) and after (0 hits for
`.claude-scratch` in a fresh `frob check --ticket T-3181 --no-cache`
run).

PRESERVED THE OBSERVATION: its content (the T-3122 close-guard
false-fire, seen once, and a separate sqlite "database is locked" crash
under concurrent `frob check` load) is migrated verbatim into a new
ticket, filed as T-3217 (numeric id assigned on land),
following the T-3131 standard the parent ticket named: it was already
NOT reproduced (direct guard-function calls returned clean, CLI retries
timed out rather than reproducing), so it is filed as a one-sighting
observation with its load conditions recorded, not as open
investigative work -- with an explicit "try to reproduce first, drop if
it doesn't" instruction for whoever picks it up.

### Changed
```
 tickets/T-3181/ticket.md           |   3 ++
 tickets/T-3217/ticket.md | 107 +++++++++++++++++++++++++++++++++++++
 2 files changed, 110 insertions(+)
```

### Evidence
- `cmd:sh -c 'echo tracked-scratch-count=$(git ls-files -- .claude-scratch/ | wc -l); test $(git ls-files -- .claude-scratch/ | wc -l) -eq 0' exit=0 sha256=2445dd9c006a` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 95 error(s), 703 warning(s), 882 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3181, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
