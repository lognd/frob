---
id: T-0587
title: Wire real TS/C/C++ test collectors (vitest/ctest) into gate evidence
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/
- tests/test_testing.py
- pyproject.toml
- .frob-release.json
- uv.lock
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_testing.py
  reason: collector tests mirroring the existing rust/python collector test coverage
    in the same test module, required by TEST001/COV gates and the ticket's own plan
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: REL001 requires a version bump (0.89.0 -> 0.90.0) for this ticket's new
    public API surface (collect_ts_tests/collect_cpp_tests); pyproject.toml/uv.lock/.frob-release.json
    are the mechanical files that bump touches
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 requires a version bump (0.89.0 -> 0.90.0) for this ticket's new
    public API surface (collect_ts_tests/collect_cpp_tests); pyproject.toml/uv.lock/.frob-release.json
    are the mechanical files that bump touches
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: REL001 requires a version bump (0.89.0 -> 0.90.0) for this ticket's new
    public API surface (collect_ts_tests/collect_cpp_tests); pyproject.toml/uv.lock/.frob-release.json
    are the mechanical files that bump touches
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 requires a CHANGELOG.md entry accompanying every version bump; main
    advanced with T-0616's un-bumped API surface (arch SRP checks) between my warm-up
    merge and land, so this bump (0.90.0 -> 0.91.0) and its changelog entries cover
    both T-0616 and T-0587
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_no_projects_is_ok_empty
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_degrades_when_npx_absent
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_genuine_failure_is_err
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_skips_malformed_entries
- tests/test_testing.py::TestFindVitestProjects::test_ignores_node_modules_package_json
- tests/test_testing.py::TestFindVitestProjects::test_ignores_project_without_vitest_dep
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_no_projects_is_ok_empty
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_unconfigured_build_is_ok_empty
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_degrades_when_ctest_absent
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_genuine_failure_is_err
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_unparseable_json_is_err
- tests/test_testing.py::TestFindCmakeProjects::test_skips_build_dir_copy_of_cmakelists
designated_repro_test: null
threat: null
component: null
---
T-0552 added TEST013 (WARN) to surface every frob:tests edge whose TEST001-004 credit rests solely on the ts/c/cpp structural name/path fallback (frob.gates._edge_is_native_unverified) instead of real execution -- but it deliberately does NOT withdraw that credit, since no real TS/C/C++ collector exists yet (src/frob/testing/ only has collect_python_tests and collect_rust_tests, T-0092) and withdrawing credit outright would turn every native-language public symbol's TEST001 ERROR-red in every sibling repo overnight, for a structural change alone. This ticket is the real fix: wire vitest (TS) and ctest (C/C++) runners (frob.testing._runners already has a RunnerSpec/RunnerOutcome shape collect_rust_tests followed for T-0092 -- mirror it), producing real node ids frob.gates._valid_edges can match the same way it already matches pytest/cargo. Once real collectors exist, retire the structural-fallback branch of frob.gates._edge_is_native_unverified (or gate it behind 'no collector configured for this language') and consider promoting TEST013 findings on a collector-covered language to ERROR.

TEST-pool triage (T-draft-edbf1e26, 2026-07-22): re-measured `frob check --only test` -- TEST013 currently reports 0 findings in this repo (this project has no ts/c/cpp public symbols under structural-fallback credit today); the real collector work this ticket tracks remains outstanding for whichever sibling repo actually exercises that fallback, unaffected by this pass.