---
id: T-3664
title: 'win32: archgate examined-sites paths use native separators'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/__init__.py
- tests/gates_suite/test_waive.py
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
Windows CI run 33521416410 (tracked by T-3659): both tests in tests/gates_suite/test_waive.py::TestWaive004ExaminedSitesGuard fail on win32 only:
- test_examined_archgate_site_is_deleted (expects 1 WAIVE004 fix applied to src/examined.py, gets 0)
- test_original_55_waiver_incident_shape_partial_examination_still_refuses (expects waive004_applied == ["src/examined.py"], gets [])

Root cause: src/frob/arch/__init__.py's analyze_project builds ArchResult.files_examined via `files_examined.append(str(path.relative_to(scan_root)))` (line ~722) -- str() on a Windows Path renders backslashes. This feeds src/frob/gates/_arch.py::arch_examined_sites, which is consumed by src/frob/gates/_coverage_sites.py::site_examined (T-1921/T-1942's per-site examined-sites substrate). site_examined's own family reporters (e.g. this module's own _perf_examined_sites/_strata_examined_sites) already normalize via `.relative_to(root).as_posix()` -- arch/__init__.py's files_examined is the one outlier still using bare str().

src/frob/gates/_fix_engine_sync.py's _drop_unexamined_archgate_candidates calls site_examined(stats, "archgate", file) with `file` coming from a WAIVE004 Violation.file (repo-relative POSIX, per every other gate's own convention). On win32, arch_examined_sites returns backslash-separated members ("src\\examined.py"), so `file in examined` (posix "src/examined.py") never matches -- every archgate-family WAIVE004 candidate is dropped as "not confirmed examined", silently deleting nothing, exactly the guard's own conservative fail-closed design working correctly on a false input.

Fix direction (product, not test): src/frob/arch/__init__.py line ~722, change `str(path.relative_to(scan_root))` to `path.relative_to(scan_root).as_posix()`.

Traceback evidence: scratchpad/win-33521-failures.txt lines 19784-20893 (examined_archgate_site_is_deleted) and lines 20896-22034 (original_55_waiver_incident_shape).

References T-3659 (tracking ticket for this campaign).
