## Done report

`_POS`-anchored `recursive-grep`'s negative pattern (T-2908) required the
scoped path token to be IMMEDIATELY followed by `[|;&]|$`. The extremely
common `2>&1 | ...` shape -- redirect stderr into the pipe -- sits
between the path and the pipe and defeated that lookahead, so a
genuinely-scoped command like `grep -rn 'foo' src/frob/verify/_watermark.py
2>&1 | head -30` still blocked with no usable alternative.

Reproduced directly this session (first-hand: `uv run ty check --help
2>&1 | grep -iE ...` was blocked by raw-linters -- a different rule, but
the same underlying `_shellscan`/negative-pattern shape -- and re-running
it exactly did NOT clear the block, contrary to the hook's own message;
see the ticket-runner note on defects (b)/(c) which are NOT part of this
ticket's scope and were reported separately, not folded in here).

Directly for T-2932's own recursive-grep case: added a regression test
(test_recursive_grep_stays_quiet_when_scoped_with_a_trailing_redirect)
and confirmed it FAILS at the parent commit (frob-suggest.py reverted
via patch/checkout roundtrip, denial reason present) with the exact
`recursive-grep` denial the ticket describes, then passes with the fix.
Also added a must-fire twin
(test_recursive_grep_still_fires_unscoped_with_a_trailing_redirect)
confirming the redirect tolerance does not swallow the genuinely-
unscoped case (`grep -rn 'foo' . 2>&1 | ...` must still block).

Fix: the negative pattern now tolerates zero or more redirect clauses
(`>`, `>>`, `<`, each optionally fd-numbered and/or fd-duplicated --
`2>&1`, `1>&2`, `>out.txt`, `2>/dev/null`) between the scoped path token
and the final `[|;&]|$` separator.

Edited the SOURCE at .claude/hooks/frob-suggest.py, ran
python3 .claude/hooks/sync-claude-config.py to materialize it to
~/.claude/hooks/, and confirmed `uv run frob claude sync --check`
reports 9 file(s) in sync (0 drift) before closing.

Gates: ruff format --check clean on both touched files. All 4
recursive-grep tests (2 pre-existing + 2 new) pass. Full
tests/test_hook_frob_suggest.py suite: 46/47 pass; the one failure
(TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it)
is a pre-existing, unrelated escalation/TTL-marker test that reproduces
identically with this ticket's diff fully reverted (confirmed via
patch/checkout roundtrip) -- a different rule (hand-rename-edit), not
recursive-grep.

### Changed
```
 .claude/hooks/frob-suggest.py   | 24 ++++++++++++++--
 tests/test_hook_frob_suggest.py | 64 +++++++++++++++++++++++++++++++----------
 tickets/T-2932/ticket.md        |  2 +-
 3 files changed, 71 insertions(+), 19 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 94 error(s), 699 warning(s), 874 waived
- error-findings: AFFECT001@.claude/hooks/frob-suggest.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2932, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
