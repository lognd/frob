---
id: T-3316
title: warn_if_xdist_bound_missing does not detect the xdist plugin's absence, only
  an unset fleet bound
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_worktree_guard.py
- tests/test_worktree_guard.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_worktree_guard.py
  reason: T-3316's plugin-absence fix is only testable via the guard's own test module
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: T-3316 adds a new doc section for warn_if_xdist_plugin_missing
  actor: logan
  at: '2026-08-28'
evidence:
- tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_fire_when_plugin_not_importable
- tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_stay_quiet_when_plugin_importable
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_also_warns_on_plugin_absence_even_without_fleet_context
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_fire_fleet_context_with_bound_missing_logs_error
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_bound_present_no_log
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_no_fleet_context_no_log
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c4d80968da0753b3ad8a0b224806423837a26d69
---
T-3276 checked this per the owner's directive: warn_if_xdist_bound_missing (tickets/_worktree_guard.py) only fires when a fleet context is detected AND PYTEST_XDIST_AUTO_NUM_WORKERS is unset in the current process's environment -- it never checks whether the pytest-xdist PLUGIN itself is importable. frob's own pyproject.toml sets -n auto in pytest addopts; in a consumer repo (or venv) with pytest-xdist not installed, that addopt makes every pytest invocation exit 4 with a usage error, regardless of fleet context or the bound env var -- the exact F-011 incident diax hit via frob coverage --full. T-3276 added ExternalToolStatus/scan_external_tools (doctor.py, OPTIONAL_FOR_GATE category) which now reports pytest-xdist's absence in frob doctor, but nothing yet makes an actual pytest spawn (frob coverage, frob check --only test, etc.) preflight-check the plugin's presence before adding -n auto and fail loud/fall back to serial instead of hitting the usage-error/DEGRADED path. Wire a preflight check (or reuse T-3276's scan_external_tools) into the pytest-spawning call sites.