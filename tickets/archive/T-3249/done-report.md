## Done report

Changed:
- src/frob/check/__init__.py::_STAGE_GROUPS
- src/frob/gates/_refs.py::_DEFAULT_ROOT_MANIFEST_EXEMPT
- tests/system/test_cli_perf.py::TestCheckOnlyPerf._init_perf001_fixture_repo (frob.toml REF001=warn)
- tests/system/test_cli_native_missing.py::_init_no_design_repo (frob.toml REF001=warn)
- tests/test_refs_gate.py::TestDefaultRootManifestExempt (2 new tests)

Root cause: T-2992's histogram entry A bundled 11 failures under one
"spurious REF001/PRE001/SCOPE001 under concurrent load" label. Direct
serial-isolation repro (no load at all) shows this premise is false for
7 of the 11 -- they fail deterministically, load-independent, from at
least 5 distinct unrelated causes. T-0089/T-0122's fix is confirmed
NEITHER regressed NOR too narrow (test_scaffold_dx's node id reproduces
under load with a complete, well-formed report -- no swallowed summary
-- it fails today for an unrelated reason). Full detail, evidence, and
the T-2992 correction are recorded in this ticket's own body (see the
CORRECTION section appended before close); not repeated here.

This ticket fixes 2 of the ~5 real causes (the ones cleanly scoped to
tests/system/test_cli_check.py's own STAGE_GROUPS/REF001 territory):

1. `_STAGE_GROUPS` never listed `comment_placement` (T-3218) -- same
   registered-but-unreachable omission shape T-3030 already fixed for 5
   sibling gates, just not extended to this later-added one. Added to
   `gates-fast`.
2. `_DEFAULT_ROOT_MANIFEST_EXEMPT` never listed `tickets.md` -- the same
   universal, tooling-only-read root-manifest shape already exempted
   for pyproject.toml/frob.toml/package.json/tsconfig.json (T-3019/
   T-3031). Added it, plus propagated T-3019's own REF001=warn
   adoption-baseline pattern (already used by test_cli_check.py's
   `_make_project`) to the two sibling fixtures that never got it.

The remaining ~3 causes are each unrelated, in different modules, and
filed as their own tickets rather than force-fit into this one's scope:
- TestCheckTicketLeasePinRefusal: already covered by the existing
  QUEUED, unowned T-3028 (CHECK001 firing before the lease-pin check) --
  not refiled.
- T-3264: TestNativeMissingFailsLoud SYS004 test -- unhandled
  NativeExtensionUnavailable crashes main instead of degrading to a
  SYS004 finding.
- T-3263: render_lint_gate git-ls-files WARNING log line loses
  its level prefix under pytest (frob.logging.logger._init's
  _under_pytest() empties root handlers unconditionally, defeating the
  test's own re-init workaround).
- T-3262: python-tool scaffold does not pass `frob check`
  immediately (OPAQUE001 message/site mismatch + REF001 on scaffolded
  root files T-3019's exemption list does not cover).

Filed: T-3264, T-3263, T-3262 (real ids
verified on main before citing further -- draft ids only exist in this
worktree until land). T-3028 (already queued, unowned, pre-existing --
not refiled, just cross-referenced above).

Evidence: 5 node ids bound (`frob ticket evidence T-3249`) -- the 2 new
tickets.md-exemption tests, the comment_placement stage-groups test, and
the perf/native-missing fixture tests that now pass.

Gates: `frob check --ticket T-3249 --only scope --only prework` clean
(0 errors on gate:SCOPE/gate:PREWORK/gate:PRE -- the two remaining FAILs
in that run, gate:DRIFT and gate:DSL, are pre-existing repo-wide findings
unrelated to any file this ticket touched, confirmed by inspecting each
one's own location).

### Changed
```
 tickets/T-3249/done-report.md      |  80 +++++++++++++++++
 tickets/T-3249/ticket.md           | 180 +++++++++++++++++++++++++++++++++++++
 tickets/T-3262/ticket.md |  81 +++++++++++++++++
 tickets/T-3263/ticket.md |  82 +++++++++++++++++
 tickets/T-3264/ticket.md |  64 +++++++++++++
 5 files changed, 487 insertions(+)
```

### Evidence
- `tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_root_tickets_md_is_exempt_with_no_declaration` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_nested_tickets_md_still_subject_to_ref001` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 110 error(s), 3357 warning(s), 876 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, DSL001@src/frob/gates/__init__.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_main_entry.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
