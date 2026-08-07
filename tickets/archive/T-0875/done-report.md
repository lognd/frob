## Done report

TEST-family burn-down, decompose-then-execute: the 486 baseline was stale (dominated by TEST005 which needs a coordinator coverage stamp and drops out of worktree measurement); real measurable count was 15. Fixed: 8 TEST002 accounting artifacts (directives pointed at bare class names -- repointed at real dotted node ids), 3 TEST014 leaf-name collisions (four new direct-call tests binding explicit edges), leaving 1 real natives-integration gap filed as a child, 2 pre-existing waived notes, and 1 structural coverage-stamp item for the coordinator. Post-fix measurable: 4, all accounted.

### Changed
```
 src/frob/app/clean_runner.py                       |  2 +
 src/frob/app/fmt_runner.py                         |  2 +
 src/frob/app/registry_runner.py                    |  2 +
 src/frob/perf/_collectors.py                       | 14 ++--
 src/frob/vet/_capability_modes.py                  |  2 +-
 .../unit/test_app_runners_t0875_leaf_collision.py  | 90 ++++++++++++++++++++++
 tickets.md                                         | 73 +++++++++++++++++-
 7 files changed, 175 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun::test_dry_run_reports_nothing_to_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun::test_json_mode_prints_report_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun::test_missing_registry_dir_logs_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0875_leaf_collision.py::TestFmtRunnerRun::test_check_mode_reports_all_canonical_on_empty_tree` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParsePerfScript::test_parses_committed_fixture_into_leaf_first_stacks` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseV8CpuProfile::test_parses_committed_fixture_walking_parent_chain` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestBuildClassToFile::test_maps_unambiguous_class_to_its_file` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseJfrPrint::test_parses_committed_fixture_into_leaf_first_stacks` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestDetectCollectorFormat::test_cpuprofile_extension_is_v8` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestParseCollectorFormat::test_dispatches_to_the_matching_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_collectors.py::TestBuildIndexForFiles::test_resolves_a_real_python_file_in_the_repo` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_precise_kind_passes_through` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
