## Done report

detect_project_type only checked Cargo.toml/CMakeLists.txt/pyproject.toml/
setup.py/package.json and *.cpp/*.cc/*.c at the repo TOP LEVEL; a C/C++ or
Rust project whose sources or build files live only under a subdirectory
(e.g. src/CMakeLists.txt with no root CMakeLists.txt) returned "unknown"
and silently fell through to the Python check pipeline (finding 6/T-0546),
never running the native toolchain. Added
`_detect_nested_native_project_type`: a bounded, pruned recursive fallback
scan (via `frob.excludes.iter_files`, the shared pruned-walk entry point --
no new WALK001 finding) for a nested Cargo.toml/CMakeLists.txt marker or a
bare native source file, tried only after every top-level check misses.

Cut: could not add a new dedicated regression test for the nested-detection
case under `tests/` -- `frob ticket scope --add` for
`tests/unit/test_check.py` was rejected with the same `ScopeLeaseConflict`
already logged against T-draft-0ea414ea (T-0160 holds an in-progress lease
over `tests/**`). Verified the new nested-marker/nested-source/empty-repo
paths manually via a throwaway `python -c` script (nested CMakeLists.txt ->
cpp, nested-only .cpp source -> cpp, nested Cargo.toml -> rust, empty repo
-> unknown, all as expected) but that could not be committed as a test.
The existing `TestDetectProjectType` suite in tests/unit/test_check.py
(already bound via `frob:tests` from the test side, unaffected by this
change) continues to pass and is recorded as evidence per the same
docs/guides/agent-playbook.md section 5 fallback.

### Changed
```
 src/frob/app/check_runner.py | 39 +++++++++++++++++++++++++--
 src/frob/check/__init__.py   | 43 ++++++++++++++++++++++++++++++
 tickets.md                   | 63 +++++++++++++++++++++++++++++++++++++++++---
 3 files changed, 139 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestDetectProjectType::test_cargo_toml_is_rust` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_cmakelists_is_cpp` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_no_sentinel_is_unknown` (pytest node id, verified passing when recorded)
