---
id: T-3435
title: PORT001 cannot catch a bare string-constant identity default (detection-shape
  gap)
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_port_selfcheck.py
- src/frob/gates/_waive.py
- tests/unit/gates/test_port_selfcheck.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: PORT001-DEFAULT needs registration in _waive.py's known-rule allowlist (UnregisteredGateRuleConstructed)
    and its own gate tests
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/gates/test_port_selfcheck.py
  reason: PORT001-DEFAULT needs registration in _waive.py's known-rule allowlist (UnregisteredGateRuleConstructed)
    and its own gate tests
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/gates.md
  reason: PORT001-DEFAULT is a new PORT001-family rule id; the port_selfcheck_gate
    doc anchor covering PORT001 needs updating to avoid doc drift
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_bare_default_value_is_flagged_t3435
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_bare_pkg_name_assignment_stays_quiet_t3435
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3275 (re-scope PORT001's population, do-not-fix-here for anything beyond the stated acceptance): T-3275 widened PORT001's SCANNED POPULATION to repo-wide (tracked_repo_python_files), which now includes src/frob/testing/_coverage_refresh.py -- the exact module whose hardcoded _DEFAULT_COV_TARGET = "src/frob" motivated this whole ticket (FROBLEMS.md F-011). But running the widened PORT001 against this repo does NOT flag that line: neither of PORT001's two AST shapes (PORT001-PATH: a string literal passed as a .startswith(...) argument; PORT001-IDENT: a bare package-name literal inside a Tuple/List/JoinedStr) matches a plain module-level string-constant ASSIGNMENT like _DEFAULT_COV_TARGET = "src/frob". This is a distinct gap from the population question T-3275 fixed: PORT001 now scans the right FILES but still cannot detect this particular hardcoding SHAPE. Add a third detection shape (PORT001-DEFAULT or similar): a module-level (or function-default-value) string-constant assignment whose value is exactly "src/<declared-package>" or the bare declared package name used as a full path-shaped literal. Decide tier (advisory vs behavioral) and whether it needs its own rule id or folds into PORT001-PATH.