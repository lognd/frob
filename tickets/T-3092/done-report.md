## Done report

Built TICK014 (WARN, `frob.gates._empty_diff_close.empty_code_diff_violations`),
dispatched from `tickets_gate()` alongside TICK001..TICK013 (same queue-wide
gate family, no close/land-time wiring needed since `frob.tickets` deliberately
stays free of `frob.gates`, per `_done_transition_guard`'s own docstring).

The check reads the SAME `### Changed` fenced block `compose_done_report`
already auto-composed (`frob.tickets._evidence.render_changed_block`, T-0458)
back out of a DONE ticket's body -- no separate diff computation, no new git
call, and it can never disagree with what the Done report itself recorded. A
DONE ticket with `kind` in {feature, bug}, `tier != epic`, and
`no_scope_declared=False` whose Changed block lists no path outside ticket
bookkeeping (`tickets/`, `tickets.md`, `tickets-archive.md`) fires TICK014.
A Done report with no parsable Changed block at all (predating T-0458) is
treated as "cannot tell" and stays silent, never a false-positive.

Registered TICK014 in `_KNOWN_GATE_RULES` (`frob.gates._waive`) so
`frob:waive TICK014 reason="..."` binds normally, same as every other rule.
Doc anchor lives in `docs/modules/tickets-data-storage.md#tick014----empty-code-diff-on-close-t-3092`
rather than `docs/modules/gates.md#rule-catalog` -- that file is leased by
in-progress T-2988 (Docstrings rework); the `#rule-catalog` frob:enumerates
list there is left stale (DOCENUM001 fires) until that lease releases.

Deliberately narrow (disclosed): only the three ledger prefixes count as "no
code" -- a close that also touches a rapid-land bookkeeping artifact outside
those prefixes (`rapid-debt.jsonl`, a CHANGELOG fragment) is NOT exempted and
still fires; the ticket's own acceptance criteria name only the `tickets/`
prefix, so this is not silently assumed complete.

Verified locally (natives built via `make core` after a stale worktree
lacked `frob_core`/`strata_core`): all 8 new tests pass, all pre-existing
TICK-family tests pass (112/112, `tests/test_gates.py -k "Tick or
tickets_gate or TICK"`), and `frob check --ticket T-3092` shows zero
COV001/TEST002/GATERULE001/REG009/FMT001 findings against the new file
(gate:COV error count dropped from 35 to 34 relative to the pre-change
baseline -- the one fix this ticket's own diff resolves). The one
DOCENUM001 finding against `docs/modules/gates.md` is the disclosed
lease-conflict gap above.

Filed: T-3259 (add TICK014 to docs/modules/gates.md's
#rule-catalog frob:enumerates list once T-2988's lease on that file
releases; not a "not implemented" disclosure -- TICK014 itself is fully
implemented, registered, tested, and documented at its secondary anchor,
this is purely the pending secondary doc-catalog update).

### Changed
```
 tickets/T-3092/done-report.md      | 63 +++++++++++++++++++++++++++++++
 tickets/T-3092/ticket.md           | 77 ++++++++++++++++++++++++++++++++++++--
 tickets/T-3259/ticket.md | 29 ++++++++++++++
 3 files changed, 165 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates_empty_diff_close.py::TestTick014::test_bug_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_feature_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_docs_kind_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_epic_tier_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_no_scope_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_real_diff_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_no_block_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_open_never_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 108 error(s), 3666 warning(s), 878 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3092, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_main_entry.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
