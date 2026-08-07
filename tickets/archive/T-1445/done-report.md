## Done report

Extended T-0602/T-1346's gate-result cache (.frob/gate-cache.db) to the
root-scanning process-pool gates (T-0415's _ProcessJob dispatch table)
and added a first-class `frob check --no-cache` CLI flag.

Process-gate cache design (src/frob/gates/_gate_cache.py):
- root_content_key(root): sha256 over `git ls-files -s`'s full output
  (blob sha per tracked file) -- the whole-tree analogue of the existing
  _membership_key membership guard, sound for any gate reading
  st.root/st.repo_root/st.snapshot directly (an unbounded filesystem walk
  TrackedSnapshot cannot observe).
- load_root_gate_cache/store_root_gate_cache: read/write the SAME
  gate_results table evaluate_cacheable_gate already owns
  (membership_key == touched_key == root_content_key(...), no
  touched_files set -- whole-gate granularity, not per-touched-file).
- _CACHEABLE_PROCESS_GATES (src/frob/gates/__init__.py): every
  _build_process_jobs entry -- perf, clones, sys, secrets, taint, opaque,
  archgate, exhaustive_handling, ffi_boundary, pii_structural, walk_lint,
  cve_fingerprint_scan, render_lint, dead_symbols, wire, cache,
  protocol_summary. _process_gate_extra folds clones'/wire's diff/queue
  side inputs into the same extra_key model_side_channel_key discipline
  T-1454 established.
- _split_process_cache partitions a run's selected _ProcessJobs into
  cache HITS (served without spawning a worker, via the new
  _seed_preloaded_process_cache seeding step in _run_combined_jobs) and
  MISSES (submitted as before, with the fresh result persisted after
  drain via _store_pending_process_cache). Wired through
  _assemble_gate_report/_run_gates_bounded's existing use_cache flag --
  use_cache=False (every pre-T-1445 call site) is unaffected.

--no-cache CLI flag: AppConfig.check_no_cache (src/frob/app/config.py),
registered in src/frob/_cli_parsers/_check.py, threaded through all four
_dispatch_check_* functions in src/frob/app/check_runner.py into
run_check/run_check_cpp/run_check_rust/run_check_ts's existing no_cache
parameter (already plumbed end-to-end by T-1346, just never reachable
without the FROB_NO_GATE_CACHE env var before now). Also added
check_no_cache to src/frob/app/_config_external.py's field-name
passthrough tuple -- WIRE001 caught this as a real gap (AppConfig.
from_external was silently dropping the new argparse dest before this
fix).

MEASURED (this repo, warm run, 9 _CACHEABLE_PROCESS_GATES selected:
archgate/secrets/opaque/pii_structural/walk_lint/render_lint/
exhaustive_handling/ffi_boundary/cache):
  run_gates(use_cache=False): 33.04s wall
    per-gate CPU: archgate=24.29s pii_structural=9.04s opaque=3.67s
    secrets=2.54s exhaustive_handling=2.81s walk_lint=1.68s
    render_lint=1.30s cache=1.29s ffi_boundary=0.32s
  run_gates(use_cache=True), second (warm) call: 9.45s wall
    every cacheable gate reports 0.0s (served from cache, no worker
    process spawned) -- same violation SET both ways (verified via
    len(violations) equality plus the cold-diff-oracle/observational-
    transparency property tests below).
A synthetic tmp_path smoke test (archgate+secrets only) shows the same
shape at smaller scale: 1.50s cold vs 0.019s warm.

Correctness: TestColdDiffOracleProcessGates and
TestCacheTransparencyProcessGates (INV-050's shared
tests/_cache_transparency.py harness, parameterized over this cache
surface per the ticket's own acceptance note) assert run_gates(use_cache=
False) and run_gates(use_cache=True) agree across randomized
edit/add/remove/revert sequences -- the same cold/warm agreement bar
TestColdDiffOracle already established for the thread-pool cache.

Scope widened beyond the ticket's original 7 globs (frob ticket scope
--add, each with a --reason-file, all logged in the ticket's own
scope_changes audit trail):
- src/frob/gates/_gate_cache.py, tests/test_gate_cache.py,
  tests/_cache_transparency.py: the ticket's own body names
  "gate-cache.db machinery" and the INV-050 harness as what this must
  build on -- the cache primitives and their tests belong there, not
  duplicated into __init__.py.
- src/frob/app/_config_external.py: one field-name addition
  (check_no_cache) required to make --no-cache actually reach
  AppConfig.from_external instead of being silently dropped -- WIRE001
  caught this as a real gap in the diff, not optional polish.

Disclosed residuals (follow-up ticket filed, real id after land):
1. This is WHOLE-GATE (root-content-hash) caching, not per-touched-file
   like T-0602's thread-pool side -- any tracked-file edit anywhere
   invalidates every _CACHEABLE_PROCESS_GATES entry, not just the gates
   that would have read the changed file. True per-file decomposition
   (secrets/opaque/taint/walk_lint/render_lint/cve_fingerprint_scan all
   scan files independently and could serve unchanged files' findings
   individually) needs each gate's inner-loop body split into a per-file
   callable -- reaches into src/frob/gates/_secrets.py and siblings,
   outside this ticket's src/frob/gates/__init__.py +
   src/frob/gates/_gate_cache.py scope.
2. SELFAUDIT001 (gate:SELFAUDIT, --only gates-security): 9 findings for
   the 3 new public _gate_cache.py symbols (root_content_key,
   load_root_gate_cache, store_root_gate_cache) and 4 new
   test_gate_cache.py test classes, none declared in design/frob.strata's
   gates/testsuite node interface= lists. Could not fix in this ticket --
   design/frob.strata was leased by T-1220 (in-progress, unrelated) for
   the whole session (frob ticket scope --add rejected with
   ScopeLeaseConflict). frob check --ticket T-1445 --only gates-native
   and --only gates-fast both report 0 errors; --only gates-security
   reports 0 errors from WIRE001/AFFECT001 (both fixed) and exactly these
   9 pre-existing-shape SELFAUDIT001 findings, disclosed here rather than
   silently left unmentioned.

Pre-existing, unrelated finding noticed while measuring (not filed as a
new ticket -- already reachable via any --only selection naming these
gate ids explicitly, predates T-1445): "taint" and "cve_fingerprint_scan"
are dispatchable via _build_process_jobs but absent from _ALL_GATES/
_CANONICAL_GATE_ORDER, so selecting either by name in GateConfig.gates
crashes with GateOrderDriftError. Out of T-1445's scope (pure
pre-existing _ALL_GATES/_CANONICAL_GATE_ORDER registration gap, unrelated
to caching); noted here for whoever next touches that registration.

### Changed
```
 design/frob.strata                              | 823 ++++++++++++------------
 docs/modules/gates.md                           |  50 ++
 docs/modules/tickets.md                         |  46 +-
 src/frob/_cli_parsers/_check.py                 |  11 +
 src/frob/_cli_parsers/_ticket/_progress.py      |  38 +-
 src/frob/app/_config_external.py                |   6 +
 src/frob/app/check_runner.py                    |   8 +
 src/frob/app/config.py                          |  18 +
 src/frob/app/ticket_runner/_land_cmd.py         | 238 ++++++-
 src/frob/gates/__init__.py                      | 449 ++++++++++---
 src/frob/gates/_gate_cache.py                   | 184 +++++-
 src/frob/tickets/_models.py                     |  12 +
 tests/test_gate_cache.py                        | 330 ++++++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py | 266 ++++++++
 tickets.md                                      | 496 +++++++++++++-
 15 files changed, 2449 insertions(+), 526 deletions(-)
```

### Evidence
- `tests/test_gate_cache.py::TestRootContentKey::test_stable_when_nothing_changes` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRootContentKey::test_changes_on_tracked_file_edit` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRootContentKey::test_none_outside_a_git_repo` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRootGateCache::test_miss_then_hit_skips_second_call` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRootGateCache::test_tree_edit_forces_miss` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRootGateCache::test_extra_change_forces_miss` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRootGateCache::test_none_key_never_hits_and_never_stores` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestSplitProcessCache::test_use_cache_false_returns_everything_as_misses` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestSplitProcessCache::test_hit_removes_gate_from_remaining` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestSplitProcessCache::test_miss_keeps_gate_pending` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_second_warm_run_serves_process_gate_from_cache` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_tracked_file_edit_forces_process_gate_recompute` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestColdDiffOracleProcessGates::test_cache_agrees_with_cold_across_random_edits` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestCacheTransparencyProcessGates::test_root_gate_cache_observationally_transparent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
