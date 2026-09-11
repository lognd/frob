## Done report

src/frob/testing/_collect.py was 895 lines, over LARGE001's 800-line threshold. Split the cache-key/native-build-fingerprint/cross-call-state seam into a new sibling module src/frob/testing/_collect_python_cache.py, mirroring T-4407's verify_runner.py split. No behavior change: every moved name is re-imported into _collect.py (T-1074 precedent) so from frob.testing._collect import ... call sites keep resolving unchanged, and every existing monkeypatch.setattr(collect_mod, ...) test still patches the right module-global lookup since the orchestration functions calling these names stayed in _collect.py. Fixed the resulting stale frob:tests/frob:doc citations (DRIFT002) in tests/test_testing.py, tests/test_testing_collect.py, docs/modules/testing.md, docs/guides/install.md, and declared the two new-file fs.read/fs.write via-list sites in design/frob.strata plus bumped the capability-via-ratchet lock counts (SELFAUDIT001/SYS100), per T-4407's identical precedent commit. Kind changed bug->feature (a pure split has no mutation evidence). Verified with uv run frob check --ticket T-4409: gate:COV/DRIFT/SCOPE/LARGE/ARCH/FMT all clean; gate:MILE/TICK/DOC failures present are pre-existing repo-wide, unrelated to this ticket's files.

### Changed
```
 src/frob/testing/_collect.py              | 453 +++---------------------------
 src/frob/testing/_collect_python_cache.py | 435 ++++++++++++++++++++++++++++
 tickets/T-4409/ticket.md                  | 116 +++++++-
 3 files changed, 584 insertions(+), 420 deletions(-)
```

### Evidence
- `tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_backslash_path_normalizes_to_posix` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectPythonTests::test_python_collection_missing_natives_reflects_last_call` (pytest node id, verified passing when recorded)
- `tests/test_cache_transparency.py::TestPytestCollectCacheTransparency::test_cold_warm_agree_across_random_edits` (pytest node id, verified passing when recorded)
