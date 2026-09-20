---
id: T-4409
title: _collect.py exceeds LARGE001 800-line threshold
state: done
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