---
id: T-1124
title: 'arch: app runner abstraction-opportunity remainder (check_runner 2 groups,
  deploy_runner, perf_runner) -- T-1085 residue'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/deploy_runner.py
- src/frob/app/perf_runner.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_json_mode
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_and_heat_round_trip
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_deploy_stages_appended_when_deploy_dir_present
- tests/unit/perf/test_persist_run_cli.py::TestPersistRunDefaultPath::test_missing_perf_path_resolves_to_cwd
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only arch scoped to src/frob/app WHEN the remaining abstraction-opportunity
    groups are extracted or dispositioned with grounded reasons THEN zero unaccounted
    findings remain in check_runner.py, deploy_runner.py, and perf_runner.py
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_deploy_stages_appended_when_deploy_dir_present
threat: null
component: null
---
T-1085 extracted the genuine _load_snapshot/_CACHE_REL duplicate into frob.app._snapshot and deliberately cut the rest to limit app/ contention during wave 17: check_runner.py's two ToolResult-builder groups (the skip/unavailable/disabled constructors look like a genuine extraction), deploy_runner.py's repeated-name (Path) -> str group, and perf_runner.py's _heat/_collect pair. Per T-1085's body: check the repeated-name groups FIRST for a literal same-file shadowing duplicate (possibly dead code) before assuming distinct functions. Re-measure counts before starting; T-1112's detector exclusion may change them.