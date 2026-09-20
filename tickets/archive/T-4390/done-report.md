## Done report

Coordinator measurement, Windows CI run 34415921529 (head 7ad69b30f, which includes T-4382): the Windows self-gate reports `gate:COV 56 errors`, still dominated by COV003 firing on the SAME `tests/unit/test_stackdump.py`-family evidence T-4382's fix targets -- so T-4382's platform-skip attribution did not take effect on that runner.

Traced the cause to `collect_python_tests`'s own pre-existing code comment (T-4382 itself documented this as a known, out-of-scope gap): a pytest-collection cache HIT returns without ever calling `_run_collect_only`, so `_platform_skipped_test_modules()` reads back `()` even when the original (cache-MISS) collection found platform-skipped modules -- `.frob/pytest-collect.json` only ever stored node ids, never skip reasons. The Windows job's own workflow runs a TEST step (`frob test`) BEFORE the self-gate `frob check` step, both against the same checkout, so `frob check`'s own internal collection call hits a cache the earlier TEST step already warmed -- exactly this gap, live.

Fix: added an optional `extra` JSON payload to the shared node-id cache (`_load_cache_extra`/`_store_cache` in `_collect_shared.py`) -- additive only, every existing 3-positional-arg `_store_cache` call site (rust/ts/ctest/kotlin collectors) is unaffected since `extra` defaults to `None`. `collect_python_tests` now round-trips `platform_skipped` through it on both the cache-store and cache-hit paths, instead of resetting to `()` on a hit.

Verified as a genuine repro: committed the new test alone first, ran `frob ticket evidence --check-repro --base-ref <test-only-commit>`, got `FAILED_AT_PARENT` (the test genuinely fails without the fix -- confirmed manually too by checking out just the fix files and re-running), then committed the fix.

### Changed
- `src/frob/testing/_collect_shared.py::_load_cache_extra` (new)
- `src/frob/testing/_collect_shared.py::_store_cache` (gained optional `extra` param)
- `src/frob/testing/_collect.py::collect_python_tests` (round-trips `platform_skipped` through the cache's `extra` payload on both store and cache-hit paths)

### Evidence
- `tests/test_testing_collect.py::TestPlatformSkippedSurvivesCacheHit::test_platform_skipped_round_trips_through_a_cache_hit` (verified as a genuine repro via `--check-repro`)

Filed: none new. Part of the same session's Windows-only self-gate series as T-4386 (TEST002 platform-skip); gate:TICK/DRIFT/LARGE Windows findings are tracked separately in this session.
