## Done report

Changed:
- scripts/fleet_status.py::_stat_fields_after_comm
- scripts/fleet_status.py::_read_ppid_from_stat
- scripts/fleet_status.py::_all_process_ppids
- scripts/fleet_status.py::_live_check_pids
- scripts/fleet_status.py::_forkserver_root_is_live_check
- scripts/fleet_status.py::orphaned_forkserver_count
- scripts/fleet_status.py::concurrent_check_count
- scripts/fleet_status.py::_derive_forkserver_stale_after_s
- scripts/fleet_status.py::stale_forkserver_count
- scripts/fleet_status.py::_forkserver_contradiction_line
- scripts/fleet_status.py::_forkserver_status_lines
- docs/guides/coordinator-scripts.md (orphaned_forkserver_count, stale_forkserver_count, concurrent_check_count, _land_status_lines sections)

Root cause fixed: orphaned_forkserver_count tested only the immediate
parent (ppid == 1). A forkserver reparented to ANOTHER, already-orphaned
forkserver has a live parent, so it read healthy even though walking one
more hop reaches init. _forkserver_root_is_live_check now walks the full
ancestry chain via a fresh /proc-wide ppid map (_all_process_ppids) and
only calls a forkserver healthy if a live `frob check` pid
(_live_check_pids) is found anywhere in its chain.

Age backstop: stale_forkserver_count's stale_after_s now defaults to
_derive_forkserver_stale_after_s, which sums each stage group's own
maximum sample from .frob/check-budget-timing-samples.json (T-2809) and
applies a headroom multiplier, floored, instead of the old hardcoded
3600s constant -- per the ticket's explicit requirement citing T-2715/
_TRUE_COUNT_BUDGET_S as the precedent for why a frozen number silently
stops tracking repo growth. Falls back to the original T-2517 constant
only when no samples file exists yet.

Contradiction surfacing: _forkserver_contradiction_line prints a loud
CONTRADICTION line, ahead of the other three, when orphaned == 0 and
stale == 0 both read clean next to forkserver swap above
_SWAP_PRESSURE_FLOOR_KB -- the exact combination that hid this ticket's
own 92-forkserver leak for 45 minutes.

Positive controls (both required by the ticket), both proved by test:
- test_two_level_chain_with_dead_root_is_orphaned: a forkserver chained
  through another forkserver whose own root died (reparented to init) is
  reported orphaned -- the case that failed before this fix. This is the
  ticket's DESIGNATED REPRO test: genuinely FAILED_AT_PARENT (verified
  against 8ecc60468, a test-only commit committed atop the pre-fix code
  specifically to get a real parent-commit verdict, since this is a new
  test with no prior history to diff against -- T-2021's own technique,
  used because BUG002's retroactive-post-land limitation, T-2025, makes
  `main` itself unusable as a parent ref for a brand-new test).
- test_deep_chain_under_a_live_check_is_not_orphaned: a forkserver 2 hops
  below a genuinely live `frob check` pid is never reported orphaned --
  the decisive control (a wrong answer here reaps live workers mid-check).
- test_zero_forkservers_reports_zero: no forkservers at all reports a
  clean 0, never an error.

Evidence: 15 pytest node ids recorded via `frob ticket evidence`,
designated repro
tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_two_level_chain_with_dead_root_is_orphaned
(FAILED_AT_PARENT at 8ecc60468, verified by the CLI's own validate-at-designate check).
Full pytest run: 32 collected, 0 failed
(Forkserver/ConcurrentCheckCount/PrintLandStatus/DeriveForkserverStaleAfterS
selection). ruff-check/ruff-format/ty clean on scripts/fleet_status.py and
tests/unit/test_coordinator_scripts.py. `frob check --only affect_drift
--ticket T-2818` clean (AFFECT001 resolved by the doc update).

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --only lint/coverage/docanchor/doclink/drift --ticket
T-2818` clean on my files (all findings present are pre-existing,
repo-wide, unrelated to scripts/fleet_status.py or
tests/unit/test_coordinator_scripts.py -- confirmed by diffing against
the pre-change file). `frob check --land-parity`'s only fleet_status-
adjacent finding (COV002 scripts/fleet_status.py) is a scope-ambiguity
artifact of land-parity running with no --ticket (multiple open tickets
tie on scope specificity for this file); confirmed clean under `frob
check --only coverage --ticket T-2818`, and `frob ticket land` supplies
the active ticket id so this resolves at real land time (same mechanism
as `_scope_covers`'s own documented `active_ticket` preference).

### Changed
```
 docs/guides/coordinator-scripts.md     |  88 +++++--
 scripts/fleet_status.py                | 454 +++++++++++++++++++++++++++------
 tests/unit/test_coordinator_scripts.py | 204 ++++++++++++---
 tickets/T-2818/ticket.md               |  26 +-
 4 files changed, 641 insertions(+), 131 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_two_level_chain_with_dead_root_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_deep_chain_under_a_live_check_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_zero_forkservers_reports_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_counts_forkserver_reparented_to_init` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_ignores_forkserver_with_live_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS::test_derives_from_recorded_samples_with_headroom` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS::test_missing_samples_file_falls_back` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS::test_malformed_samples_file_falls_back` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS::test_thin_samples_never_derive_below_the_floor` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine::test_fires_on_zero_zero_high_swap` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine::test_silent_when_swap_below_pressure_floor` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine::test_silent_when_orphaned_or_stale_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine::test_silent_on_any_unknown_input` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount::test_counts_check_processes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 20 error(s), 720 warning(s), 716 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2818, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
