## Done report

Root cause (measured on the RUNNER, not the mirror): CI run 34735688390
(Windows leg, T-4450's diagnostics step, log excerpt
/tmp/frob-coord/win-5.log lines 1505-1525) -- after the full Test step,
`.frob/pytest-collect.json` (1.5 MB) had top-level keys `['key',
'node_ids']` ONLY, no `platform_skipped` term at all, and a LIVE
`collect_python_tests(root).platform_skipped` call served from that
cache HIT returned `()`. T-4390's own extra-payload mechanism
(`_store_cache`/`_load_cache_extra`) only omitted the `platform_skipped`
key from `extra` when the tuple was empty (`extra=... if platform_skipped
else None`), so an old-format entry (predating T-4390) and a fresh
genuinely-empty entry were indistinguishable on read -- both degrade to
`()`. T-4450's cache wipe stays in place as defence in depth; this
ticket closes the actual gap so a stale/old-format hit can never serve a
wrong answer even if the wipe is skipped or races.

Changed:
- src/frob/testing/_collect.py::collect_python_tests
  (frob:ticket T-4449)

Fix: `_store_cache` now always persists `extra.platform_skipped` (even
`[]`) on write; `collect_python_tests` now treats a cache hit whose
`extra` lacks the `platform_skipped` key at all as a MISS (old-format or
any writer that omitted it), forcing a fresh `_run_collect_only` instead
of silently reading `()`.

Evidence (frob:tests T-4449):
- tests/unit/test_collect_python_cache.py::TestPlatformSkippedCacheWriteFormat::test_empty_platform_skipped_still_written
- tests/unit/test_collect_python_cache.py::TestPlatformSkippedCacheWriteFormat::test_nonempty_platform_skipped_round_trips
- tests/unit/test_collect_python_cache.py::TestOldFormatCacheEntryIsAMiss::test_old_format_entry_has_no_platform_skipped_key
- tests/test_testing_collect.py::TestOldFormatCacheForcesRecollection::test_old_format_cache_entry_triggers_fresh_collection
  (designated repro: FAILED_AT_PARENT at 68f53a91c per `frob ticket evidence --check-repro`)
- tests/test_testing_collect.py::TestPlatformSkippedSurvivesCacheHit::test_platform_skipped_round_trips_through_a_cache_hit

Filed: none (no out-of-scope discoveries requiring a new ticket; two
in-diff obligations outside T-4449's declared scope -- SELFAUDIT001 on
the new tests' fixture fs.io and AFFECT001 on collect_python_tests's
doc anchor -- were resolved without touching out-of-scope files: the
fixture I/O was rerouted through already-declared testsuite via-list
sites (tests.conftest._write, _load_cache_extra) instead of raw
Path.write_text/read_text, and AFFECT001 was waived with follow_up
T-4449, same shape as src/frob/app/ticket_runner/_close_cmd.py's own
T-1146 AFFECT001 waiver and src/frob/gates/_narrative_blocks.py's own
SELFAUDIT001 waiver, both citing design/frob.strata as out of scope).

Gates: `frob check --ticket T-4449` clean (0 errors, exit 0) after
rebase onto current main; the only FAIL row is `ruff-format` on
tests/test_tickets_triage_dates.py, pre-existing drift this ticket
never touched.
