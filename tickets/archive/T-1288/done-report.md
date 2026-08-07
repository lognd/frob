## Done report

Changed:
tests/unit/test_natives_build.py::TestBuildNatives::test_unparseable_frob_toml_is_err_load_failed
tests/unit/test_natives_build.py::TestBuildNatives::test_crate_dir_outside_root_falls_back_to_absolute_display

Evidence:
tests/unit/test_natives_build.py::TestBuildNatives::test_unparseable_frob_toml_is_err_load_failed
tests/unit/test_natives_build.py::TestBuildNatives::test_crate_dir_outside_root_falls_back_to_absolute_display

Before: local scoped coverage run (pytest tests/unit/test_natives_build.py
--cov=src/frob/natives --cov-branch) showed src/frob/natives/_build.py
short two branches: the `load_natives(...).is_err` path inside
build_natives (only the "no [[native]] entries" NoNatives case was
covered, not a genuinely unparseable frob.toml surfacing LoadFailed), and
the `except ValueError` fallback inside `_build_one_crate` for when a
resolved crate dir is not actually underneath root (Path.relative_to
raising).

After: src/frob/natives/_build.py at 100% branch coverage (99/99->100%,
22/22 branches). Added test_unparseable_frob_toml_is_err_load_failed
(malformed TOML content in frob.toml asserts build_natives returns
Err(NativesError.LoadFailed), distinct from the empty-declarations
NoNatives case already covered) and
test_crate_dir_outside_root_falls_back_to_absolute_display (monkeypatches
_resolve_buildable_crate to return a directory outside root, calls
_build_one_crate directly, asserts the recorded CrateBuildResult.crate_dir
falls back to the absolute path string instead of raising).

CrateBuildResult.ok, BuildReport.ok, and build_natives (the three
0.0%-branch symbols named on the ticket) are all live: CrateBuildResult.ok
and BuildReport.ok are exercised by the pre-existing TestCrateBuildResult
AndReport tests, and build_natives is exercised throughout the existing
suite plus the two new tests above; none are dead code.

Filed: none (no out-of-scope discoveries).

Gates: `frob check --ticket T-1288 --only test` (foreground) reports 0
TEST005 findings under src/frob/natives/**; only repo-wide TEST006/
TEST011/TEST012 (stale coverage.xml/lock, coordinator-owned `make
coverage` re-stamp) and unrelated TEST003/TEST014 warnings outside this
package's scope remain. `pytest tests/unit/test_natives_build.py -q
--cov=src/frob/natives --cov-branch` passes 22/22 tests clean at 100%
statement and 100% branch coverage for the package.

### Changed
```
 tests/test_clean.py              |  18 ++
 tests/test_fuzz.py               |  61 ++++++
 tests/unit/test_cycle.py         |  18 ++
 tests/unit/test_gitlog.py        |  75 ++++++++
 tests/unit/test_natives_build.py |  52 ++++++
 tickets.md                       | 391 ++++++++++++++++++++++++++++++++++++---
 6 files changed, 594 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/test_natives_build.py::TestBuildNatives::test_unparseable_frob_toml_is_err_load_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_crate_dir_outside_root_falls_back_to_absolute_display` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
