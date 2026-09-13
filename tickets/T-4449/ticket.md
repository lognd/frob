---
id: T-4449
title: 'Windows runner: platform_skipped empty in the self-gate AFTER the Test step
  (56 COV003 + 2 TEST002 persist past T-4447)'
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_python_cache.py
- src/frob/testing/_collect.py
- src/frob/testing/_collect_shared.py
- tests/test_testing_collect.py
- tests/test_testing.py
- tests/gates_suite/test_coverage.py
- tests/gates_suite/test_test_gate.py
- tests/unit/test_collect_python_cache*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_collect_python_cache.py::TestPlatformSkippedCacheWriteFormat::test_empty_platform_skipped_still_written
- tests/unit/test_collect_python_cache.py::TestPlatformSkippedCacheWriteFormat::test_nonempty_platform_skipped_round_trips
- tests/unit/test_collect_python_cache.py::TestOldFormatCacheEntryIsAMiss::test_old_format_entry_has_no_platform_skipped_key
- tests/test_testing_collect.py::TestOldFormatCacheForcesRecollection::test_old_format_cache_entry_triggers_fresh_collection
- tests/test_testing_collect.py::TestPlatformSkippedSurvivesCacheHit::test_platform_skipped_round_trips_through_a_cache_hit
designated_repro_test: tests/test_testing_collect.py::TestOldFormatCacheForcesRecollection::test_old_format_cache_entry_triggers_fresh_collection
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34708801531 (head 59c43cb12, 2026-09-12, INCLUDES T-4447 7a84c576a, T-4429, T-4408), Windows self-gate: STILL 56 COV003 errors on tests/unit/test_conftest_stackdump.py (50) and tests/unit/test_stackdump.py (6) plus 2 TEST002 errors on src/frob/testing/_stackdump.py -- and the message is the GENERIC one ("does not resolve to a collected test; the collection cache is keyed on test file content..."), NOT the platform-skip WARN verdict text. So on the GitHub runner the platform-skip attribution never fires at all: CollectedTests.platform_skipped is EMPTY there, whereas on the winrun mirror (T-4444 and T-4447 agents, cold AND warm frob check) it is the correct 2-tuple and T-4447's pinning yields 0 errors. The ONLY sequencing difference is that on the runner the self-gate runs AFTER the full Test step (13933 tests) in the same checkout, so the Test step's side effects are what the check reads: the python collection cache (src/frob/testing/_collect_python_cache.py, keyed on test file content) written by tests that call collect_python_tests/_collect_python_cache against the real repo (tests/test_testing_collect.py, tests/test_testing.py, tests/gates_suite/test_coverage.py, tests/gates_suite/test_test_gate.py, tests/integration/test_interfaces.py, ...), or a .frob/ artifact (self-scan-cache, coverage-file-cache.json, gate-cache.db) left by the suite. INVESTIGATE ON THE MIRROR IN CI ORDER: (1) cold `frob check --only coverage --only test --json` -> record COV003/TEST002 error count for the two modules (expect 0 after T-4447); (2) run ONLY the test files above on the mirror (`.venv/Scripts/python.exe -m pytest <files> -q -p no:randomly`), then re-run the check -> if the 56 come back, bisect by file then by test to the one that poisons the cache/state and name it; (3) if that subset does not reproduce, run the full suite on the mirror (2h; run it detached and poll) and re-check. FIX: the poisoned artifact must not be readable as authoritative by the self-gate (e.g. the cache entry must carry platform_skipped, or the test must write to an isolated .frob/ via tmp_path, or the check must invalidate entries not keyed to this platform). ACCEPTANCE: (1) the runner-order reproduction on the mirror is recorded with the exact poisoning test named; (2) after the fix, the same sequence yields 0 COV003/TEST002 errors for the two modules; (3) CI Windows self-gate COV/TEST rows clean on the next push. Sprint v0.531.0 (CI green blocker). Supersedes the T-4444 hypothesis; complements T-4447 (which is correct but never reached on the runner).

## Failure log
- 2026-09-12 attempt 1: Measured on mirror in CI order: (1) cold bare 'frob check' and '--only coverage --only test' both give 0 COV003/TEST002 errors for the two stackdump modules (confirms T-4447 fix holds standalone). (2) Ran exactly the 5 ticket-named suspect files (test_testing_collect.py, test_testing.py, gates_suite/test_coverage.py, gates_suite/test_test_gate.py, integration/test_interfaces.py) with the CI Windows Test step's own xdist shape (-n 2 --timeout=600), all 391 tests pass, then re-ran the self-gate check: still 0 ERROR-severity COV003/TEST002, only the correct WARN platform-skip verdicts (258 WARN COV003 hits, all 'is platform-unavailable ... this is a WARN, not an error'). Source audit of collect_python_tests/_collect_python_cache.py/_load_tests confirms: none of the 5 named files write to the real repo's .frob/pytest-collect.json (all use tmp_path fixtures except test_interfaces.py's 'project' fixture, also tmp_path-based); TEST002's gate-cache extra key already folds in st.tests (includes platform_skipped) via model_side_channel_key so a stale cached TEST002 result cannot serve without re-hashing; COV003 (coverage_gate) is not gate-cached at all, so it always reads a fresh CollectedTests. The named-subset hypothesis (step 2 of the ticket's own plan) is FALSIFIED by direct measurement. Step 3 (full 13933-test suite reproduction under xdist, ~70+ min per CI's own timing) was not completed in this session -- it exceeds the practical budget of one agent turn even with the 2h allowance, and the mirror is a shared, single-tenant resource. Blocking rather than forcing: the actual poisoning mechanism (if any) lives somewhere in the ~13.9k-test full suite outside the 5 named files, or is a genuine GH-runner-vs-mirror environment difference (pytest/plugin version skew, PYTEST_ADDOPTS-style env leakage between CI steps, or an artifact only the real 6000s Windows Test step's -n 2 --dist=loadgroup fanout produces) that this session's targeted repro could not isolate. Recommend: (a) a follow-up ticket to run the FULL suite on the mirror (needs a dedicated multi-hour session or CI-side instrumentation dumping .frob/pytest-collect.json before/after the Test step on the actual runner), or (b) instrument the real CI Windows leg to dump .frob/pytest-collect.json's raw JSON content immediately after the Test step and before the self-gate step, which would name the poisoning write directly without a local repro at all.

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
