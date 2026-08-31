## Done report

Implemented both halves in tests/conftest.py, same file as the ticket's
own hook homes:

1. pytest_collection_modifyitems (the same hook that assigns the
   frob_self_scan_heavy xdist_group) now also attaches
   @pytest.mark.timeout(1200) to every test in that group, right next to
   the xdist_group marker -- membership and the raised budget can never
   desync, since one hook assigns both in the same loop iteration.

2. _cached_self_scan(cache_dir, tree_hash, compute) is a small, directly
   testable caching primitive: on a cache hit (a readable, unpickle-able
   file at cache_dir/<tree_hash>.pkl) it returns the persisted result
   without calling compute; on a miss (file absent OR unreadable/
   corrupted) it calls compute() exactly once, persists the result via
   an atomic Path.replace (a worker that dies mid-write never leaves a
   torn file for the next reader), and returns it. _repo_tree_hash
   (HEAD sha + `git status --porcelain` hash, so uncommitted edits
   invalidate the cache too) never raises -- any git failure is a fixed
   fallback sentinel, i.e. a guaranteed cache miss, never a hard error.
   frob_self_scan_artifacts now wraps its real build_graph+sys_gate call
   through this primitive, persisting under this repo's own
   .frob/self-scan-cache/ (survives an xdist worker's death, unlike
   tmp_path_factory's session temp dir, which a FRESH worker process
   does not share). .build_result is now always None (no current
   consumer reads it -- confirmed by grep; was previously the raw
   GraphSnapshot on a fresh scan, inconsistent with what a cache hit
   could ever supply).

MUST-FIRE, at two levels:
 - Primitive level (TestCachedSelfScan.test_cache_hit_does_not_recompute):
   a second _cached_self_scan call with the SAME tree_hash never calls
   compute again.
 - Process level (TestCachedSelfScan.test_must_fire_scan_count_is_one_
   across_a_simulated_worker_restart): two SEPARATE subprocess Python
   invocations (a fresh interpreter each -- the actual "worker restart"
   shape T-3525 fixes, not just an in-process fixture-scope repeat)
   share the same cache dir and tree hash; a FROB_SELF_SCAN_COUNTER_FILE
   env var (test-only instrumentation _cached_self_scan itself honours,
   never set in a real run) records one line per REAL compute call
   across both processes. Asserts exactly one line -- scan-count==1
   across the simulated restart. PASSING.

MUST-STAY-QUIET:
 - test_tree_hash_mismatch_triggers_exactly_one_fresh_scan: a DIFFERENT
   tree hash is its own independent cache miss -- exactly one fresh
   compute call for the new hash, the first hash's cached entry
   untouched.
 - test_corrupted_cache_falls_back_to_a_fresh_scan: a torn/garbage cache
   file is treated as a miss, never an unpickle crash.
 - test_self_scan_heavy_tests_share_one_xdist_group (existing test,
   updated): every affected item still gets exactly the xdist_group
   marker it always did, PLUS the new timeout(1200) marker -- verified
   directly, not just "did not regress".
All PASSING (30 collected, 0 failed, tests/unit/test_conftest_stackdump.py
+ tests/unit/test_conftest_suite_result_status.py).

Real repo self-scan tests (tests/system/test_frob_self_model.py) could
NOT be exercised in this worktree: `strata_core`'s native extension is
not built here (`uv sync` alone, no `make core` -- a pre-existing
environment gap in this ephemeral worktree, confirmed present before any
of this ticket's edits and unrelated to the caching/timeout change:
build_graph itself succeeds, the failure is entirely inside sys_gate's
own design-file parsing, the SAME code path with or without this
ticket's fixture wrapper). CI's own workflow builds natives in a prior
step (make core), so this gap does not carry to the real target
environment; noted here rather than silently worked around.

Acceptance ("the next two consecutive ubuntu CI runs complete to 100%")
is an operational outcome this land cannot itself verify -- the coded
fix (raised per-group timeout + cache-on-restart) directly targets the
measured mechanism (run 33342928809), and the MUST-FIRE/MUST-STAY-QUIET
tests above are the pre-merge evidence for it.

### Changed
```
 tests/conftest.py                     | 154 ++++++++++++++++++++++++--
 tests/unit/test_conftest_stackdump.py | 197 +++++++++++++++++++++++++++++++++-
 tickets/T-3525/ticket.md              |  35 +++++-
 3 files changed, 371 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestRepoTreeHash::test_stable_for_the_same_clean_tree` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestRepoTreeHash::test_falls_back_without_raising_when_git_is_unavailable` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_cache_miss_computes_once_and_persists` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_cache_hit_does_not_recompute` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_tree_hash_mismatch_triggers_exactly_one_fresh_scan` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_corrupted_cache_falls_back_to_a_fresh_scan` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_must_fire_scan_count_is_one_across_a_simulated_worker_restart` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 24 error(s), 4087 warning(s), 899 waived
- error-findings: ARCH103@src/frob/tickets/_leases.py, COV003@tests/unit/test_land_queue.py, COV003@tests/unit/test_mutation_sweep_queue.py, COV003@tests/unit/test_process_lock.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3525/tests/unit/strata/test_litmus_cwe.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3525, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, SELFAUDIT001@tests/conftest.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
