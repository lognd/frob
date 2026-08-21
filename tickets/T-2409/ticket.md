---
id: T-2409
title: no kotlin test collector (test_discovery capability gap)
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_kotlin.py
- src/frob/testing/_collect.py
- src/frob/testing/_collect_shared.py
- src/frob/testing/__init__.py
- docs/modules/testing.md
- tests/test_testing.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_collect.py
  reason: wiring collect_kotlin_tests into the existing re-export/dispatch surface
    (frob.testing._collect re-imports every per-language collector for backward-compat
    import paths; frob.testing.__init__ re-exports the public API; _collect_shared.py
    needs a _KOTLIN_CACHE_REL cache-file constant mirroring the other three languages')
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/testing/_collect_shared.py
  reason: wiring collect_kotlin_tests into the existing re-export/dispatch surface
    (frob.testing._collect re-imports every per-language collector for backward-compat
    import paths; frob.testing.__init__ re-exports the public API; _collect_shared.py
    needs a _KOTLIN_CACHE_REL cache-file constant mirroring the other three languages')
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/testing/__init__.py
  reason: wiring collect_kotlin_tests into the existing re-export/dispatch surface
    (frob.testing._collect re-imports every per-language collector for backward-compat
    import paths; frob.testing.__init__ re-exports the public API; _collect_shared.py
    needs a _KOTLIN_CACHE_REL cache-file constant mirroring the other three languages')
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/testing.md
  reason: docs/modules/testing.md#public-api frob:doc target for collect_kotlin_tests;
    tests/test_testing.py is where the sibling per-language collectors' tests live,
    needed for TEST001 evidence on the new public function
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_testing.py
  reason: docs/modules/testing.md#public-api frob:doc target for collect_kotlin_tests;
    tests/test_testing.py is where the sibling per-language collectors' tests live,
    needed for TEST001 evidence on the new public function
  actor: logan
  at: '2026-08-18'
- op: add
  glob: design/frob.strata
  reason: 'SYS100: collect_kotlin_tests reads gradle build files/JUnit XML reports
    via read_text/read_bytes, same fs.read capability sibling collectors (_collect_cpp.py/_collect_rust.py/_collect_ts.py)
    already declare on the same node'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_parses_and_caches
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_groovy_plugin_form
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_no_projects_is_ok_empty
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_unreported_project_is_ok_empty
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_falls_back_when_source_unresolvable
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_skips_malformed_report
- tests/test_testing.py::TestCollectKotlinTests::test_collect_kotlin_tests_non_kotlin_gradle_project_is_ok_empty
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b6440bcea6869a208994c3d57c31362558c620bb
---
T-2365's adapter-capability conformance axis (frob.lang._support.derive_capability_registry) marks test_discovery KNOWN_GAP for kotlin: frob.testing has collect_python_tests/collect_rust_tests/collect_ts_tests/collect_cpp_tests but no kotlin collector, even though frob.lang has a real kotlin grammar (T-0723). Add collect_kotlin_tests mirroring collect_ts_tests's shape (or the closest JVM-toolchain analogue) and wire it into frob.testing.__init__.