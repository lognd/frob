---
id: T-3267
title: Migrate SCAN001 whole-repo-scan-timeout detector from tests/gates/ into a real
  frob-check gate rule
state: queued
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
- src/frob/gates/_scan_timeout.py
- src/frob/gates/__init__.py
- tests/gates/test_scan_timeout_enforcement.py
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
T-3247 implemented the whole-repo-scan @pytest.mark.timeout enforcement as a self-verifying repo test (tests/gates/test_scan_timeout_enforcement.py::find_scan_timeout_violations + TestRepoIsScanTimeoutClean) rather than a src/frob/gates rule wired into _assemble_gate_report, because src/frob/gates/__init__.py was under a live T-3196 scope lease at the time and could not be edited. Once T-3196 releases the lease, migrate find_scan_timeout_violations (and its AST helpers: _imported_origins, _has_timeout_override, _class_level_timeout_override, _module_level_assigns, _derives_from_dunder_file, _run_call_has_no_path_argument, _calls_whole_repo_scan_entrypoint, ScanTimeoutViolation) into a proper gate module (e.g. src/frob/gates/_scan_timeout.py) registered in _assemble_gate_report as rule SCAN001, so it participates in frob check --json/--only gates/waive accounting like every other rule, instead of only running as a pytest test. Keep the must-fire/must-stay-quiet fixtures; they still apply unchanged.