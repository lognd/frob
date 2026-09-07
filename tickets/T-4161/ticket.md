---
id: T-4161
title: route xdist-plugin-presence preflight check through the project env
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
blocked_by:
- T-3936
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3887 F-018 (remainder): frob.tickets._worktree_guard._xdist_plugin_present() checks importlib.metadata in FROB's own interpreter, not the checked project's own uv-managed env -- warn_if_xdist_plugin_missing's preflight warning can stay silent (project genuinely lacks pytest-xdist) or fire a false positive (frob lacks it but the project has it) depending on which interpreter happens to match. T-4148 fixed the DOMINANT symptom (the actual pytest spawn in frob.testing._coverage_refresh now routes through uv run --project <root>, so a real missing-plugin failure surfaces as a loud pytest exit-4 UNMEASURED result through the project's own env, never silently green) but deliberately left this preflight check alone: _xdist_plugin_present's exact zero-arg signature is pinned by three tests in tests/test_worktree_guard.py (TestWarnIfXdistPluginMissing.*), which is under an active T-3936 lease at filing time -- changing it without touching that test file risks a false pass/regression neither this ticket's own test suite nor T-3936's could catch. Fix once T-3936's lease clears: add a project-env subprocess probe (uv run --project <root> python -c ...importlib.metadata..., mirroring frob.process._project_tool's _WHICH_PROBE shape) and update warn_if_xdist_plugin_missing plus its three pinned tests together.