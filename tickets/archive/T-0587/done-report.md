## Done report

Wired real vitest and ctest test collectors into frob.testing, mirroring
collect_rust_tests's per-project discovery/cache/degrade shape:

- collect_ts_tests: discovers every package.json declaring a `vitest`
  dependency (node_modules pruned), runs `npx vitest list --json` per
  project, parses `(file, name)` pairs into `path::name` node ids, caches
  on package.json + test-file content hash. Degrades to an empty Ok result
  (warning, not a hard failure) when `npx` is absent; a genuine vitest
  failure is still Err(CollectFailed).
- collect_cpp_tests: discovers CMakeLists.txt project roots, looks for an
  already-configured conventional `build/CTestTestfile.cmake`, runs
  `ctest --test-dir <dir> --show-only=json-v1` (the documented CMake
  json-v1 schema), caches on the CTestTestfile.cmake content hash (the
  file ctest itself reads, so it fully determines the answer). Node id
  anchors to `<build_dir>::<test name>` (KNOWN APPROXIMATION -- ctest
  tests have no required source-file locality, same class of
  approximation as the existing rust integration-binary symref). Degrades
  to an empty Ok result when `ctest` is absent; a malformed/unparseable
  json payload or nonzero exit from an installed ctest is still Err.
- Both exported from frob.testing; both new public functions carry
  `frob:doc docs/modules/testing.md#public-api` (the existing anchor
  collect_rust_tests already points at) and `frob:ticket T-0587` on every
  new symbol.

Deliberately NOT done (out of declared scope, filed as T-0730 (ex-draft, id lost at land)):
wiring collect_ts_tests/collect_cpp_tests into frob.gates._load_tests so
_valid_edges actually credits them, and retiring/downgrading the ts/c/cpp
structural name/path fallback in _edge_is_native_unverified. T-0587's own
scope is src/frob/testing/ (+ this ticket's tests/test_testing.py,
pyproject.toml, .frob-release.json, uv.lock scope extensions for the
mandatory REL001 version bump) -- frob/gates/__init__.py is a separate
module the ticket does not glob.

Scope was extended three times via `frob ticket scope --add` (not by
hand-editing frontmatter), all logged in the ticket's scope_changes audit
trail: tests/test_testing.py (fixture-backed collector tests, required by
the ticket's own plan and TEST001/COV002); pyproject.toml/.frob-release.json
/uv.lock (the mechanical files a REL001-mandated version bump touches); and
CHANGELOG.md (a second bump, 0.90.0 -> 0.91.0, was required after a
mid-ticket `git merge main` pulled in T-0616's un-bumped arch SRP API
surface -- both T-0616's and T-0587's changelog entries are recorded).

Correction from an earlier review round: the gates-wiring follow-up is
filed as T-0730 (ex-draft, id lost at land) (verified present in tickets.md via grep before
this report was finalized) -- an earlier claim of a lost draft (superseded by T-0730) in this
same Done report was wrong (that id was minted during this session but its
ticket block was lost to an out-of-order ledger-restore mistake and never
re-created before the report was written; the reviewer caught it).

### Changed
```
 .frob-release.json           |  14 +-
 pyproject.toml               |   2 +-
 src/frob/testing/__init__.py |   4 +
 src/frob/testing/_collect.py | 381 ++++++++++++++++++++++++++++++++++++++++++-
 tests/test_testing.py        | 336 ++++++++++++++++++++++++++++++++++++++
 uv.lock                      |   2 +-
 6 files changed, 732 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_no_projects_is_ok_empty` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_degrades_when_npx_absent` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_genuine_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_skips_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestFindVitestProjects::test_ignores_node_modules_package_json` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestFindVitestProjects::test_ignores_project_without_vitest_dep` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_no_projects_is_ok_empty` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_unconfigured_build_is_ok_empty` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_degrades_when_ctest_absent` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_genuine_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_unparseable_json_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestFindCmakeProjects::test_skips_build_dir_copy_of_cmakelists` (pytest node id, verified passing when recorded)
