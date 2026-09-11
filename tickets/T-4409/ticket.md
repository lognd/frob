---
id: T-4409
title: _collect.py exceeds LARGE001 800-line threshold
state: in-progress
kind: feature
origin: human
created: '2026-09-10'
priority: medium
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: v0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect.py
- src/frob/testing/_collect_python_cache.py
- docs/guides/install.md
- docs/modules/testing.md
- tests/test_testing.py
- tests/test_testing_collect.py
- tests/unit/test_pytest_spawn_env_wiring.py
- src/frob/testing/_collect_shared.py
- frob.lock
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_collect_python_cache.py
  reason: T-4409's LARGE001 split extracts cache/native-fingerprint helpers into this
    new sibling module
  actor: logan
  at: '2026-09-11'
- op: add
  glob: docs/guides/install.md
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: docs/modules/testing.md
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: tests/test_testing.py
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: tests/test_testing_collect.py
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: tests/unit/test_pytest_spawn_env_wiring.py
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: src/frob/testing/_collect_shared.py
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: frob.lock
  reason: T-4409's LARGE001 split moves symbols whose frob:doc/frob:tests edges and
    cache-key dependency land in these files -- scope closure
  actor: logan
  at: '2026-09-11'
- op: add
  glob: design/frob.strata
  reason: T-4409's LARGE001 split moves fs.read/fs.write call sites into the new sibling
    module; SELFAUDIT001/SYS100 requires declaring them, per T-4407's identical precedent
  actor: logan
  at: '2026-09-11'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: T-4409's LARGE001 split moves fs.read/fs.write call sites into the new sibling
    module; SELFAUDIT001/SYS100 requires declaring them, per T-4407's identical precedent
  actor: logan
  at: '2026-09-11'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3505
  reason: windows drain epic T-3505 covers this leaf
  actor: logan
  at: '2026-09-11'
- field: kind
  old_value: bug
  new_value: feature
  reason: pure module split, no behavior change -- a split has no mutation evidence,
    matches T-4407's precedent
  actor: logan
  at: '2026-09-11'
evidence:
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_backslash_path_normalizes_to_posix
- tests/test_testing.py::TestCollectPythonTests::test_python_collection_missing_natives_reflects_last_call
- tests/test_cache_transparency.py::TestPytestCollectCacheTransparency::test_cold_warm_agree_across_random_edits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LARGE001: src/frob/testing/_collect.py is 895 lines, over the 800-line threshold, and will red the next ubuntu self-gate. Filed for tracking only per coordinator brief -- another agent owns this file and the COV/TEST gate attribution around it; do NOT dispatch a fix here without coordinating, extract a cohesive private module the same way T-4407 split verify_runner.py.
## Done report

Changed:
- src/frob/testing/_collect.py (895 -> ~450 lines): kept the `pytest --collect-only`
  invocation/parsing seam (spawning the collector, parsing node ids, unioning
  nested `[[test.runner]] cwd` projects, `collect_python_tests`,
  `LANGUAGE_COLLECTORS`, `__all__`)
- src/frob/testing/_collect_python_cache.py (new): extracted the cache-key/
  native-build-fingerprint/cross-call state seam (`_content_key`,
  `_native_fingerprint`/`_missing_natives`/`_autorebuild_missing_natives`,
  `_collection_cache_key`, `drop_collection_cache`,
  `python_collection_failure_detail`/`python_collection_missing_natives`/
  `_platform_skipped_test_modules` and their setters, `_parse_platform_skipped`,
  `_python_runner_cwds`/`_is_nested_python_runner`, `_walk_test_files`/
  `_find_test_files`) -- mirrors T-4407's verify_runner.py split. No behavior
  change; every moved name is re-imported into _collect.py (T-1074 precedent)
  so `from frob.testing._collect import ...` call sites keep resolving
  unchanged, and every existing `monkeypatch.setattr(collect_mod, ...)` test
  still patches the right module-global lookup since the orchestration
  functions that call these names stayed in _collect.py.

Evidence:
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_backslash_path_normalizes_to_posix
- tests/test_testing.py::TestCollectPythonTests::test_python_collection_missing_natives_reflects_last_call
- tests/test_cache_transparency.py::TestPytestCollectCacheTransparency::test_cold_warm_agree_across_random_edits
- full runs green: tests/test_testing_collect.py (13/13), tests/test_testing.py (115/115),
  tests/test_cache_transparency.py (5/5)

Filed: none

Gates: uv run frob check --only ruff clean (0 errors; the 1 ruff-format warning on
src/frob/gates/__init__.py is pre-existing, outside scope). uv run frob check
--only archgate: gate:LARGE clean for both files in scope (the 1 unwaived
LARGE001 remaining repo-wide is src/frob/app/verify_runner.py, T-4407's own
file, pre-existing and out of this ticket's scope). Scope amended (--add
src/frob/testing/_collect_python_cache.py) but the ledger mirror to main is
blocked by a concurrent land in progress (T-4401) -- worktree-local edit only,
needs a re-run from the primary once the repo is quiet (same LandInProgress
class as this session's own T-4425 filing).
