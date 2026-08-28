## Done report

Changed:
- src/frob/process/_reap.py::_read_ppid_from_stat
- src/frob/process/_reap.py::_forkserver_cmdline_matches
- src/frob/process/_reap.py::_is_live_check_process
- src/frob/process/_reap.py::_all_process_ppids
- src/frob/process/_reap.py::_forkserver_root_is_live_check
- src/frob/process/_reap.py::reap_orphaned_forkservers
- src/frob/process/_reap.py::_is_frob_check_process

Diagnosis (before any fix): T-2849/T-2880's PDEATHSIG mechanism itself
works. Directly reproduced the exact scenario it defends against
(timeout -s KILL 5 uv run python <script constructing a real
frob.gates._open_process_pool>) and confirmed zero surviving
forkserver/worker processes afterward. The reported "23 orphaned
forkservers, no live frob check ancestor" was substantially a
MEASUREMENT ARTIFACT of a regex bug, not a real second leak path:
scripts/fleet_status.py's `_FROB_CHECK_TOKEN_RE = re.compile(rb"(?:^|/)
frob\x00")` only anchors `^` to the WHOLE cmdline blob's start, never to
each NUL-delimited argv token, so a bare `frob` token that is neither
the first token nor preceded by a literal `/` -- exactly the shape
`python -m frob check ...` produces, the fleet's own dominant invocation
form under `uv run` -- never matches. Confirmed live 2026-08-27: two
running `python -m frob check ...` launchers (pids 707388, 823429) were
both alive at the moment fleet_status.py reported all 9 of their
descendant forkservers as ORPHANED.

`scripts/fleet_status.py` itself is out of T-3072's scope
(src/frob/process/_reap.py only) -- filed as residue for T-draft-*
(CLI-wiring half) and folded into T-3093 (fleet_status.py half, already
named as an audit target there).

Separately, and genuinely in scope: this file carried the SAME broken
regex a second time (`_is_frob_check_process`'s own
`_FROB_TOKEN_RE`/`_CHECK_TOKEN_RE`), undercounting `count_running_checks`
for the same invocation shape, and `reap_orphaned_forkservers` itself
used only a ONE-HOP `ppid == 1` check (`_is_orphaned_forkserver`),
missing T-2818's own documented gap: a forkserver reparented to ANOTHER,
already-orphaned forkserver (that intermediate forkserver is itself
alive, so a one-hop test on the pid below it reads "live parent").

Fix: `_is_live_check_process` (whole-token comparison, no regex, no
anchor bug possible) replaces both broken copies.
`_forkserver_root_is_live_check` (T-2818's own multi-hop-walk algorithm,
reimplemented here since `frob.process` cannot import from `scripts/` --
the dependency only runs the other direction) replaces the one-hop check
in `reap_orphaned_forkservers`. Verified live: spun up a real `frob
check --only gates` background process, confirmed its forkserver
descendant correctly recognized as live-parented (would-reap == []) even
under `age_floor_s=0.0`.

Must-fire: a forkserver reparented to an already-orphaned forkserver
(two-hop chain, root ppid=1) is reaped.
Must-stay-quiet (the one that matters most): a forkserver several hops
below a genuinely running check -- invoked the fleet's own dominant way,
`python -m frob check ...` -- is never reaped, at any depth, even when
old enough and every intermediate hop is itself a forkserver.

Test-first proof: tests/unit/test_process_reap.py committed alone first
(e629e1fc8), confirmed ImportError (collection failure) at that commit
for the new symbols; the fix commit (7f899d2e9) followed. --designate-
repro against e629e1fc8 confirms FAILED_AT_PARENT for
TestForkserverRootIsLiveCheck::test_orphaned_forkserver_of_forkserver_is_orphaned.

Evidence: 14 node ids bound (see evidence list on the ticket).

Filed: T-3106 -- fix scripts/fleet_status.py's own copy of the
same regex bug (folded into T-3093, already scoped there) and add a
first-class "frob process reap" CLI command (CLI-wiring, outside this
ticket's single-file scope).

Gates: frob check --ticket T-3072 to run at land.

### Changed
```
 src/frob/process/_reap.py          | 262 +++++++++++++++++++++++++++++++------
 tests/unit/test_process_reap.py    | 173 ++++++++++++++++++++++++
 tickets/T-3072/ticket.md           |  21 ++-
 tickets/T-3106/ticket.md |  75 +++++++++++
 4 files changed, 487 insertions(+), 44 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_forkserver_of_orphaned_forkserver_is_reaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_forkserver_under_a_live_check_is_never_reaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_terminates_old_orphaned_forkservers` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_leaves_young_orphaned_forkservers_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_leaves_non_forkserver_processes_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_missing_proc_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsLiveCheckProcess::test_matches_module_invoked_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsLiveCheckProcess::test_matches_executable_path_invoked_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsLiveCheckProcess::test_does_not_match_unrelated_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsLiveCheckProcess::test_does_not_match_check_repro_subcommand` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck::test_direct_child_of_live_check_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck::test_orphaned_forkserver_of_forkserver_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck::test_deep_chain_under_a_live_check_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_counts_other_check_processes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 88 error(s), 711 warning(s), 862 waived
- error-findings: AFFECT001@src/frob/process/_reap.py, ARCH001@src/frob/process/_reap.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@src/frob/tickets/_land_compose.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_land_compose.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@src/frob/process/_reap.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@src/frob/process/_reap.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@src/frob/process/_reap.py, E501@/home/logan/projects/frob/.claude/worktrees/series-bk/src/frob/process/_reap.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bk/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3072, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE001@tests/unit/test_process_reap.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
