---
id: T-4386
title: TEST002 must attribute platform-skipped stackdump edges, not error
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
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
Measured on Windows CI run 34371162715 (win4.log): frob check on Windows reports gate:TEST FAIL 2 errors -- both are TEST002 findings on src/frob/testing/_stackdump.py::dump_all_thread_stacks and ::install_stackdump_handler (frob.toml promotes TEST002 to error via T-3844's zero-finding-batch [gates.severity] override; TEST006/TEST003/TEST014 stay warn per frob.toml comments and are not part of the 2 errors). Root cause: each function's sole frob:tests edge points at tests/unit/test_stackdump.py, which pytest.skip(..., allow_module_level=True)s the whole module on win32 (SIGUSR1 is POSIX-only) -- so _valid_edges finds 0 collected cases and _test001_002_one falls into the generic _test002_below_min WARN, which the frob.toml override then promotes to ERROR, indistinguishable from a genuinely undertested symbol. Same COLLECTION-EXCLUSION shape T-4382 just fixed for COV003 (reuse CollectedTests.platform_skipped, do not re-derive): when a TEST001/002 record's unit edges point ENTIRELY into a platform_skipped test module, attribute via a distinct verdict naming the excluding platform/reason instead of the plain below-min WARN that TEST002's error override then blindly promotes. Also close the adjacent gap this exposes: _apply_severity_overrides in _waive.py currently promotes ANY severity (including Severity.UNRESOLVED measurement-gap verdicts like T-4138's _test002_unmeasured) to the configured severity, which would silently defeat this same platform-skip attribution (and T-4138's) the moment TEST002 is overridden to error -- guard it to never escalate an UNRESOLVED verdict.