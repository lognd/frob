---
id: T-0875
title: 'TEST-family warning burn-down: per-symbol coverage campaign, gate:TEST to
  zero (486 baseline)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun::test_dry_run_reports_nothing_to_clean
- tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun::test_json_mode_prints_report_json
- tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun::test_missing_registry_dir_logs_and_returns
- tests/unit/test_app_runners_t0875_leaf_collision.py::TestFmtRunnerRun::test_check_mode_reports_all_canonical_on_empty_tree
- tests/unit/perf/test_collectors.py::TestParsePerfScript::test_parses_committed_fixture_into_leaf_first_stacks
- tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_parses_committed_fixture_walking_parent_chain
- tests/unit/perf/test_collectors.py::TestBuildClassToFile::test_maps_unambiguous_class_to_its_file
- tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_parses_committed_fixture_into_leaf_first_stacks
- tests/unit/perf/test_collectors.py::TestDetectCollectorFormat::test_cpuprofile_extension_is_v8
- tests/unit/perf/test_collectors.py::TestParseCollectorFormat::test_dispatches_to_the_matching_adapter
- tests/unit/perf/test_collectors.py::TestBuildIndexForFiles::test_resolves_a_real_python_file_in_the_repo
- tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_precise_kind_passes_through
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check at close WHEN gate:TEST evaluates THEN it reports
    zero warnings, with every resolution a real test or a reasoned per-symbol disposition,
    never a blanket waiver
  evidence:
  - tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun::test_dry_run_reports_nothing_to_clean
threat: null
component: testing
---
T-0204 child (test family). gate:TEST reports 486 warnings at 2026-07-23 baseline, dominated by TEST005 per-symbol no-direct-coverage warnings (plus TEST002/TEST014/TEST011/TEST003/TEST012/TEST006 stragglers). Zero-warnings requires per-symbol test coverage or explicit per-symbol disposition. This is a campaign: recount at start, group by package, and split into per-package sub-tickets if any package exceeds a session (this child is the accounting). Interacts with T-0589 (promote TEST005/TEST015 into TEST001 credit) -- coordinate so written tests satisfy the promoted rule, not just silence the warning.