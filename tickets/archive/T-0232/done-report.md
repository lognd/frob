## Done report

Changed:
- src/frob/gates/__init__.py::_timed_job (new) -- wraps a gate job to
  self-report `time.thread_time()` (CPU time consumed by the worker
  thread it actually runs on), measured from inside that thread.
- src/frob/gates/__init__.py::_run_jobs -- now times jobs via
  `_timed_job` instead of `time.monotonic()` bracketing
  `future.result()` from the submitting thread.
- src/frob/graph/cache.py::_apply_schema -- no-ops when the on-disk
  schema already matches `_SCHEMA_VERSION` instead of unconditionally
  re-running `CREATE TABLE IF NOT EXISTS` on every `connect()`.
- src/frob/graph/cache.py::connect_readonly (new) -- a `mode=ro` sqlite
  connection (`PRAGMA query_only = ON`) that cannot request the write
  lock at all.
- src/frob/graph/__init__.py::load_graph -- opens the cache via
  `connect_readonly` instead of `connect`; a query-time
  `sqlite3.DatabaseError` (garbage/corrupt cache) is now caught here
  too and reported as `CacheCorrupt`, matching the old self-healing
  path's eventual outcome (self-healing itself is `build_graph`'s job).

Root cause found (differs from the ticket's initial framing, both
measured live on this repo, not just the P1 report):

1. **Timing attribution was genuinely wrong**, not just misleading.
   `_run_jobs` measured wall-clock elapsed per job from the submitting
   thread. Most gate jobs (`archgate`, `clones`, `decisions`, `fuzz`,
   `perf`, `release`, `secrets`, `sys`, `tickets`, ...) are pure-Python,
   CPU-bound work sharing one `ThreadPoolExecutor` -- they all contend
   for the same GIL, so wall-clock elapsed for a cheap job converges
   toward however long the *slowest* job in the batch runs, regardless
   of that cheap job's own cost. Measured on this repo before the fix:
   `sys` reported 14.63s wall vs. 2.00s of its own CPU time; `tickets`
   1.53s wall vs. 0.53s CPU; a live `frob check` run showed
   `secrets=14.01s sys=14.02s tickets=13.99s` clustering almost
   identically -- reproducing the ticket's exact reported symptom
   (`secrets=39.71s sys=39.71s tickets=39.69s`) live, no concurrent
   `frob vet` required. Switching to `time.thread_time()`, measured
   inside each job's own worker thread, isolates each job's actual CPU
   cost: after the fix the same run reports
   `secrets=1.20s sys=0.98s tickets=0.24s perf=2.66s clones=0.00s` --
   genuinely distinct numbers reflecting real relative cost.
2. **.frob db contention**: `connect()` was used even by pure readers
   (`load_graph`), and `_apply_schema` re-ran `CREATE TABLE IF NOT
   EXISTS` unconditionally on every call. A direct experiment (raw
   sqlite3, no frob) showed this specific DDL statement does NOT
   actually block against a same-process uncommitted writer once the
   schema already exists, so it was not, on its own, provably the field
   contention's root cause -- but it is still wasted work on every
   invocation, so the no-op skip stands as a real improvement.
   `connect_readonly` is the more defensible, generalizable fix for
   "reduce/eliminate .frob db contention" specifically: a caller that
   only ever reads (`load_graph`; the same connection style is now
   available to any read-only gate) can no longer contend for sqlite's
   single writer slot at all, by construction (`mode=ro` +
   `PRAGMA query_only`), rather than relying on a DDL no-op happening
   to not block in the versions of sqlite tested.

No gate was weakened: `_apply_schema`'s mismatch/rebuild path is
untouched (only the already-current-version case became a no-op, which
was always semantically a no-op); `load_graph`'s error taxonomy
(`CacheStale` vs `CacheCorrupt`) is unchanged, just also catches a
corrupt-file error one statement later than before since a read-only
connection cannot self-heal (regression test
`test_cache_corrupt_on_garbage` still passes).

Evidence:
- tests/test_gates.py::TestRunJobsTimingAttribution::test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing
  -- runs one deliberately CPU-heavy job alongside cheap jobs through
  the real `_run_jobs`; asserts each cheap job's own CPU time stays
  small and distinct from the heavy job's. Verified this fails against
  the pre-fix code (reverted locally, cheap jobs measured 1.35-1.38s vs
  heavy's 1.39s -- exactly the "shared" symptom) before confirming it
  passes against the fix.
- tests/test_graph.py::TestCacheModule::test_connect_readonly_rejects_writes_no_lock_contention
  -- pins `connect_readonly` rejects writes (`OperationalError`) and
  reads through even while another connection holds an uncommitted
  write.
- tests/test_graph.py::TestConcurrentCache::test_connect_on_current_schema_does_not_block_on_a_held_write_lock
  -- pins the `_apply_schema` no-op: `connect()` against an
  already-current-schema db returns promptly alongside an in-progress
  writer.

Filed: none.

Gates: `uv run frob check --ticket T-0232` -- 1 error, 54 warnings, 25
waived. The 1 remaining error is `REL001` (public API changed since
0.22.0: `connect_readonly` is a new public symbol) -- disclosed per
dispatch instructions, not fixed here (version bump/`frob release
stamp` is a separate release-process step, not part of this bug fix).
`uv run pytest tests/test_gates.py tests/test_graph.py -p no:cacheprovider -q`
-- all green (no failures). `uv run ruff check` /
`ruff check` (both PATH and project-pinned) and `uv run ty check` all
clean on every touched file.
