## Done report

GROUND TRUTH RE-VERIFIED (re-read `frob.process._reap`, T-3072/T-3093 fixed copies): both
`frob ops process reap` (`src/frob/process/_reap.py::reap_orphaned_forkservers`) and `scripts/
fleet_status.py::orphaned_forkserver_count` already use the SAME corrected ancestry walk (multi-
hop, "any ancestor is a live `frob check` pid" -- T-2818/T-3072), and the SAME corrected cmdline
token match (T-3093 fixed fleet_status.py's regex to match `python -m frob check`). So the
divergence was NOT the ancestry algorithm.

REAL DISCRIMINATOR: `reap_orphaned_forkservers` has ALWAYS applied `DEFAULT_ORPHAN_AGE_FLOOR_S`
(300s, `src/frob/process/_reap.py`) before ever treating a forkserver as a reap candidate --
too young = never touched, REGARDLESS of ancestry. `orphaned_forkserver_count` applied NO age
floor at all: the instant a forkserver's ancestry failed to reach a live `frob check` pid, it
counted as ORPHANED. A forkserver spawned seconds ago by a live pytest-xdist worker (a `frob
test` run, not `frob check` -- its cmdline structurally carries no `frob` token and its
ancestry structurally never reaches a `frob check` process) is exactly this shape: legitimate,
young, and permanently ancestor-less by construction. `reap`'s age floor correctly deferred
judgment on it; `fleet_status.py`'s report did not, and flagged it ORPHANED on sight -- the
measured divergence.

FIX: added `_ORPHAN_AGE_FLOOR_S = 300.0` to `scripts/fleet_status.py`, mirroring `_reap.
DEFAULT_ORPHAN_AGE_FLOOR_S` exactly (a second copy -- fleet_status.py's documented "no frob
import" contract forbids importing the canonical constant, same constraint T-3072's own Done
report already accepted for the duplicated ancestry-walk helpers). `orphaned_forkserver_count`
now skips any forkserver younger than the floor (or whose age is unmeasurable), matching
`_reap._reap_orphaned_pids`'s own `age_s is None or age_s < age_floor_s: continue` posture
exactly.

AGREEMENT MECHANISM CHOSEN: kept two copies (generating the script's copy at sync time or
shelling out to `frob ops process reap --dry-run --json` were both weighed and rejected --
neither verb exists today, and fleet_status.py's whole reason for having its own copies at all
is that it cannot import `frob`, so a sync-time codegen step would need new tooling this ticket
did not scope) PLUS a cross-check test,
`TestOrphanedForkserverCountAgreesWithReap` in `tests/unit/test_coordinator_scripts.py`, that
builds the SAME constructed `/proc` tree and runs both `fleet_status.orphaned_forkserver_count`
and `frob.process._reap`'s own classifier functions against it, asserting they reach the same
verdict for (a) a young xdist-parented forkserver (must-stay-quiet, both say not-orphaned) and
(b) an old ancestor-less forkserver (must-fire, both say orphaned/reap-candidate). This is the
ticket's own explicitly-cheapest option and would have caught this divergence itself.

A THIRD, previously-unnoticed divergence surfaced while building the cross-check fixture:
`_reap._process_start_age_s` derives age from the `<proc>/<pid>` DIRECTORY's own mtime, while
`fleet_status._forkserver_age_s` derives it from `/proc/<pid>/stat`'s `starttime` field plus
`/proc/uptime` -- two different heuristics for the same quantity, currently equivalent in
practice (both approximate process start time) but NOT provably identical (a `/proc` entry's
mtime can in principle be touched by something other than process creation). Filed as residue
below rather than fixed here (out of this ticket's declared scope, `scripts/fleet_status.py`
only -- fixing the age heuristic touches `src/frob/process/_reap.py` too).

OTHER PREDICATES CHECKED for the same too-narrow "must have frob-check ancestor" shape:
- STALE FORKSERVERS (`stale_forkserver_count`): gates entirely on `concurrent_checks == 0`
  (zero live `frob check` processes ANYWHERE on the host) -- never inspects any individual
  forkserver's own ancestry, so it cannot have this bug by construction. Confirmed clean.
- CONCURRENT CHECKS (`concurrent_check_count`): counts live `frob check` processes host-wide
  using the same T-3093-fixed token matcher; not tied to any forkserver's ancestry at all.
  Confirmed clean.
Neither shares the age-floor gap `orphaned_forkserver_count` had.

Evidence: `TestOrphanedForkserverCount` (12 tests, including 2 new must-fire/must-stay-quiet
pairs and 1 unmeasurable-age case) and `TestOrphanedForkserverCountAgreesWithReap` (2 tests)
all green; full `tests/unit/test_coordinator_scripts.py` (238 tests) and
`tests/unit/test_process_reap.py` (38 tests) green; `ruff check`/`ruff format` clean;
`frob check --ticket T-3139` gate:SCOPE clean.

Filed: T-3152 (age-heuristic divergence between fleet_status._forkserver_age_s and
_reap._process_start_age_s) -- NOT fixed in this ticket, out of its declared
`scripts/fleet_status.py`-only scope (the canonical fix also touches
`src/frob/process/_reap.py`).

### Changed
```
 scripts/fleet_status.py                | 119 ++++++++++++--
 tests/unit/test_coordinator_scripts.py | 284 +++++++++++++++++++++++++++++++--
 tickets/T-3128/done-report.md          |  70 ++++++++
 tickets/T-3128/ticket.md               |   7 +-
 tickets/T-3139/ticket.md               |   9 +-
 5 files changed, 456 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_young_forkserver_with_no_check_ancestor_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_old_forkserver_with_no_check_ancestor_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCountAgreesWithReap::test_young_xdist_parented_forkserver_agrees` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCountAgreesWithReap::test_old_no_ancestor_forkserver_agrees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 124 error(s), 924 warning(s), 872 waived
- error-findings: AFFECT001@scripts/fleet_status.py, ARCH001@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@scripts/fleet_status.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV005@scripts/fleet_status.py, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3139, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
