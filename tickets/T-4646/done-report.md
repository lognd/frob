## Done report

T-4646: over_broad_literal_globs re-reads pyproject.toml uncached per doable() lease check

## WHAT changed, per file

src/frob/lang/_nodes.py
  - Added `_pyproject_data(root)`: a per-root, mtime-invalidated memoization
    cache for the parsed `pyproject.toml` dict (same shape as T-4649's
    `_store_mode_cache`/`_store_mode_cache_signal`: stat the file, use its
    mtime -- or -1.0 if missing -- as the invalidation signal, only
    tomllib.load() on a cache miss). Guarded by `_pyproject_data_cache_lock`
    (threading.Lock) since doable() can run under multi-threaded fleet load.
  - Added `_dict_or_empty(value)`: a small narrowing helper (`value` if
    `isinstance(value, dict)` else `{}`) every nested pyproject.toml table
    lookup now shares, replacing repeated `x.get(k, {})`/isinstance checks.
  - `_declared_python_source_roots` (already had its own `lru_cache`, but
    was ALSO independently re-running `tomllib.load()` inside that cached
    function -- a second, separate read of the same file) now reads through
    `_pyproject_data` instead of parsing pyproject.toml itself.
  - `declared_project_package_name` -- THE actual defect: this function had
    NO caching at all, and did a fresh `tomllib.load()` on every single
    call. Now reads through `_pyproject_data`.
  - `declared_source_prefixes` was already just a pure function of the two
    functions above, so it benefits transitively with no code change to it
    (only a docstring note).
  - Added a module logger (`_log = get_logger(__name__)`), matching the
    rest of `frob.lang`'s logging convention -- this file previously had
    none.

src/frob/tickets/_models.py
  - `over_broad_literal_globs`: docstring updated to record the T-4646 cache
    chain it now sits behind (no code change needed -- it was already a
    pure function of `declared_source_prefixes`, so the fix flows through
    automatically once that function's own upstream calls are cached).
  - Added `frob:ticket T-4646` alongside the existing (closed) `T-2771`
    directive on `over_broad_literal_globs`, and a `frob:ticket T-4646` /
    `frob:tests` pair on the new `_dict_or_empty` helper -- both needed to
    clear COV002 (see Pre-READY checks below).

tests/unit/test_pyproject_data_memoization.py (new, added to scope via
`frob ticket scope T-4646 --add`)
  - `TestPyprojectDataMemo.test_memoized`: seeds a `pyproject.toml`, calls
    `declared_project_package_name`/`declared_source_prefixes`/
    `over_broad_literal_globs` 5x each (15 calls total) with `Path.open`
    monkeypatched to count calls against `pyproject.toml` -- asserts 0
    re-opens after the first (already-warm) call.
  - `test_invalidates_on_mtime_change`: POSITIVE CONTROL -- rewrites
    `pyproject.toml` with a DIFFERENT `[project].name` after the first
    cached call (with a 1.01s sleep to beat coarse filesystem mtime
    resolution) and asserts the answer actually flips. Proves the cache
    invalidates on a real change, not just that it returns a stale answer
    fast.
  - `test_missing_pyproject_returns_none_and_stays_cached`: a missing file
    is cheap to re-probe (one `stat()` that raises `OSError`) by design --
    asserts the (absent) `open()`/parse specifically is never attempted,
    not that `stat()` itself is skipped.
  - `test_scales_across_many_candidates_and_leases`: reproduces the
    ticket's ACTUAL defect shape directly -- 200 "candidate tickets" x 50
    "lease holders" = 10000 calls to `over_broad_literal_globs(root)`
    (doable()'s own `_leased_by_one_holder` call site), asserting the
    underlying `pyproject.toml` `open()` count stays at exactly 1, not
    10000.

## WHY

`doable()`'s `_leased_by_one_holder` (src/frob/tickets/_doable.py:671) calls
`over_broad_literal_globs(root)` once per (queued/planned candidate ticket,
in-progress lease holder) pair -- `declared_source_prefixes` ->
`declared_project_package_name` then did a bare `tomllib.load()` on EVERY
one of those calls, an O(tickets x leases) storm of fresh file reads/parses
of the exact same unchanged `pyproject.toml`. This is the same cost shape
T-4649 already fixed for `_store_mode` (also called once per candidate x
lease pair inside the same `doable()` walk) -- same fix pattern applied
here: per-root memoization keyed on the file's own mtime as the cheap
invalidation signal.

Both re-read sites the ticket named (`_models.py`'s `over_broad_literal_
globs` and `_nodes.py`'s `declared_source_prefixes`/`declared_project_
package_name`) are fixed by the SAME single cache
(`_pyproject_data`), rather than three separate caches, avoiding the
duplication a per-function cache would have introduced -- and also fixes
a fourth, previously-unnoticed independent read inside
`_declared_python_source_roots` (which had an `lru_cache` around its own
dict-walk, but was STILL parsing `pyproject.toml` itself instead of
sharing the parse).

## Acceptance proof

- `test_scales_across_many_candidates_and_leases` is the direct positive
  control for the ticket's own defect description (200 candidates x 50
  leases = 10000 calls): `pyproject.toml` `open()` count == 1, not 10000.
- `test_invalidates_on_mtime_change` proves the cache is not a silent
  staleness trap: an actual config change is detected on the very next
  call.
- `test_memoized` / `test_missing_pyproject_returns_none_and_stays_cached`
  cover the warm-cache and missing-file paths respectively.

## Timing evidence (isolated hot-path benchmark)

A full end-to-end `time frob ticket doable` run on this repo's live ledger
was attempted twice under current heavy fleet load and both times was
contaminated by unrelated in-flight work (background "rapid sweep"
subprocesses hitting their own timeouts, one run SIGTERM'd mid-flight while
reaping multiprocessing children -- see raw output saved at
/tmp/claude-1000/.../scratchpad if needed) -- not a clean signal for this
ticket's specific fix. Isolated the hot path itself instead, since it is
exactly this repo's own `pyproject.toml` and exactly the call pattern
`doable()` runs:

  AFTER (this fix, cached):      10000 calls to declared_project_package_name(root) in 0.1035s
  BEFORE (uncached, simulated -- inlines the OLD code's fresh tomllib.load()
          every call, same as declared_project_package_name did prior to
          this fix):              10000 calls in 7.8278s

~75x faster at the exact call count (200 candidates x 50 leases) the ticket
describes. Given `doable()`'s own `_leased_by_one_holder` was doing exactly
this per pair, this directly addresses the described TICK008 real-repo
timing regression (over_broad_literal_globs was the NEW dominant cost after
T-4649's _store_mode fix landed).

## Test node ids (evidence bound via `frob ticket evidence T-4646`)

tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_memoized
tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_invalidates_on_mtime_change
tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_missing_pyproject_returns_none_and_stays_cached
tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_scales_across_many_candidates_and_leases

## Commit shas (worktree t-4646, branch t-4646)

Rebuilt post hoc to split the repro test out of the fix commit (BUG002
requires a commit reachable from HEAD where the test exists AND fails,
before the fix lands on top of it -- see "Designated repro" below). Final
tree is identical to the original squashed history (verified via
`git diff` before switching branches).

60aeb5b84  chore(tickets): record T-4646 start transition
debe86a15  chore(tickets): scope T-4646
8058a6414  test(lang): add T-4646 repro test only (pre-fix)
7ee55ff62  fix(lang): memoize pyproject.toml parse used by scope-overlap checks
b7a2b6932  fix(tickets): bind T-4646 frob:ticket edges on changed public symbols
193629472  chore(tickets): record evidence for T-4646   (HEAD)

## Designated repro (BUG002)

designated_repro_test: tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_scales_across_many_candidates_and_leases
base-ref (parent-of-fix): 8058a6414897450b97e8fee1708e62fc9114c40d
  `frob ticket evidence T-4646 --designate-repro ... --base-ref 8058a6414`
    -> FAILED_AT_PARENT: genuinely fails at 8058a6414... -- a real repro
  `frob ticket evidence T-4646 --check-repro ... --base-ref 8058a6414`
    -> FAILED_AT_PARENT (re-confirmed)

## Filed follow-up tickets

none -- the pattern here (a loader called inside a nested loop over ledger
entries) is the SAME class T-4649 already fixed for `_store_mode`; no new
PERF00x detector ticket filed since this is the second, not first,
occurrence and a general detector for "loader called inside doable()'s
per-candidate x per-lease loop" would need to characterize BOTH sites to
avoid re-splitting the same finding -- left for the coordinator to decide
whether a follow-up detector ticket should cover both T-4649 and T-4646 as
one class, or file it separately; flagging here rather than silently
skipping it.

## Pre-READY checks

$ frob check --only sys --files src/frob/lang/_nodes.py --files src/frob/tickets/_models.py --files tests/unit/test_pyproject_data_memoization.py --base dev
  pass  gate:PROFILE  0 errors, 0 warnings, 0 unresolved, 0 waived
  pass  gate:WAIVE    0 errors, 8 warnings, 0 unresolved, 0 waived
  FAIL  gate:DRIFT    6 errors (pre-existing, unrelated to touched files -- rapid_sweep.py/invariants.py/_evidence.py, all pre-waived T-3799/T-4335)
  FAIL  gate:DSL      1 error (tests/test_app.py:387, pre-existing, unrelated)
  FAIL  gate:SELFAUDIT 1 error (design:1 testsuite via-list ratchet growth, pre-existing, unrelated)
  -> zero findings attributable to src/frob/lang/_nodes.py, src/frob/tickets/_models.py, or the new test file.

$ frob check --only arch --files src/frob/lang/_nodes.py --files src/frob/tickets/_models.py --files tests/unit/test_pyproject_data_memoization.py --base dev
  pass  frob-arch  20 warnings (36 waived), 546 suggestions -- none against touched files; no ARCH001/LARGE001 anywhere in the report.

$ frob check --only coverage --files src/frob/lang/_nodes.py --files src/frob/tickets/_models.py --files tests/unit/test_pyproject_data_memoization.py --base dev
  First run: FAIL gate:COV 10 errors -- 1 attributable: COV002 on
  over_broad_literal_globs (docstring edit, no open frob:ticket edge left
  since its only prior edge T-2771 is closed). Fixed by adding
  `frob:ticket T-4646` (+ frob:ticket/frob:tests on the new _dict_or_empty
  helper).
  Second run after fix: FAIL gate:COV 9 errors (one fewer) -- zero
  attributable to src/frob/lang/_nodes.py, src/frob/tickets/_models.py, or
  the new test file; remaining 9 are pre-existing repo-wide TODO002/COV
  findings on unrelated files (src/frob/gates/_coverage.py,
  src/frob/perf/_dup_spawn.py, src/frob/perf/_loop_effects.py,
  src/frob/strata/_secrets.py).

$ ruff check src/frob/lang/_nodes.py src/frob/tickets/_models.py tests/unit/test_pyproject_data_memoization.py
  All checks passed!

$ ty check src/frob/lang/_nodes.py src/frob/tickets/_models.py tests/unit/test_pyproject_data_memoization.py
  All checks passed!

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 ++-
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  68 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-3943.md                              |   2 +
 changelog.d/T-3961.md                              |   2 +
 changelog.d/T-4111.md                              |   2 +
 changelog.d/T-4116.md                              |   2 +
 changelog.d/T-4214.md                              |   2 +
 changelog.d/T-4221.md                              |   2 +
 changelog.d/T-4230.md                              |   2 +
 changelog.d/T-4413.md                              |   2 +
 changelog.d/T-4414.md                              |   2 +
 changelog.d/T-4415.md                              |   2 +
 changelog.d/T-4491.md                              |   2 +
 changelog.d/T-4492.md                              |   2 +
 changelog.d/T-4493.md                              |   2 +
 changelog.d/T-4494.md                              |   2 +
 changelog.d/T-4495.md                              |   2 +
 changelog.d/T-4496.md                              |   2 +
 changelog.d/T-4498.md                              |   2 +
 changelog.d/T-4501.md                              |   2 +
 changelog.d/T-4502.md                              |   2 +
 changelog.d/T-4503.md                              |   2 +
 changelog.d/T-4507.md                              |   2 +
 changelog.d/T-4508.md                              |   2 +
 changelog.d/T-4510.md                              |   2 +
 changelog.d/T-4511.md                              |   2 +
 changelog.d/T-4512.md                              |   2 +
 changelog.d/T-4514.md                              |   2 +
 changelog.d/T-4517.md                              |   2 +
 changelog.d/T-4519.md                              |   2 +
 changelog.d/T-4520.md                              |   2 +
 changelog.d/T-4521.md                              |   2 +
 changelog.d/T-4522.md                              |   2 +
 changelog.d/T-4523.md                              |   2 +
 changelog.d/T-4524.md                              |   2 +
 changelog.d/T-4531.md                              |   2 +
 changelog.d/T-4532.md                              |   2 +
 changelog.d/T-4535.md                              |   2 +
 changelog.d/T-4536.md                              |   2 +
 changelog.d/T-4540.md                              |   2 +
 changelog.d/T-4543.md                              |   2 +
 changelog.d/T-4547.md                              |   2 +
 changelog.d/T-4548.md                              |   2 +
 changelog.d/T-4550.md                              |   2 +
 changelog.d/T-4552.md                              |   2 +
 changelog.d/T-4553.md                              |   2 +
 changelog.d/T-4554.md                              |   2 +
 changelog.d/T-4555.md                              |   2 +
 changelog.d/T-4556.md                              |   2 +
 changelog.d/T-4562.md                              |   2 +
 changelog.d/T-4563.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 changelog.d/T-4588.md                              |   2 +
 changelog.d/T-4596.md                              |   2 +
 changelog.d/T-4607.md                              |   2 +
 changelog.d/T-4633.md                              |   2 +
 changelog.d/T-4634.md                              |   2 +
 changelog.d/T-4642.md                              |   2 +
 changelog.d/T-4649.md                              |   2 +
 changelog.d/T-4650.md                              |   2 +
 design/frob.strata                                 | 167 ++--
 docs/commands/check.md                             |  88 +-
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  87 +-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/extending/comment-dsl-directives.md    |  13 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/guides/unity.md                               |  83 ++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |  95 ++
 docs/modules/gate-time-stable-invariant.md         |  74 ++
 docs/modules/gates.md                              | 165 +++-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  37 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 +++-
 docs/modules/tickets.md                            |  70 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 frob.toml                                          |  18 +
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/__init__.py                  |   2 +
 src/frob/_cli_parsers/_check.py                    | 295 ++++++-
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 ++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       | 154 +++-
 src/frob/app/config.py                             |  92 +-
 src/frob/app/ticket_runner/__init__.py             | 125 ++-
 src/frob/app/ticket_runner/_close_cmd.py           |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 +++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 245 +++++-
 src/frob/check/__init__.py                         | 244 ++++--
 src/frob/check/_python.py                          | 152 +++-
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 ++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 +++++
 src/frob/excludes.py                               |  83 +-
 src/frob/gates/__init__.py                         | 263 +++---
 src/frob/gates/_claim_lint.py                      | 202 +++++
 src/frob/gates/_coverage.py                        | 203 ++++-
 src/frob/gates/_fix_engine.py                      |  94 +-
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_guard_closure.py                   | 301 +++++++
 src/frob/gates/_inv.py                             | 359 ++++++++
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 +++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 185 +++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_nodes.py                            | 159 +++-
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 +++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 780 +++++++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 +++++++
 src/frob/testing/_dotnet_runner.py                 | 251 ++++++
 src/frob/testing/_runners.py                       |  10 +
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/testing/_unity_batchmode.py               | 298 +++++++
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 274 +++++-
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   |  49 +-
 src/frob/tickets/_leases.py                        | 552 ++++++++----
 src/frob/tickets/_models.py                        |  80 +-
 src/frob/tickets/_registry_files.py                | 145 ++++
 src/frob/tickets/_setters.py                       | 113 +--
 src/frob/tickets/_store.py                         | 120 ++-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 +++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 +++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  75 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 +
 .../python_control/duplicate.py                    |  29 +
 tests/fixtures/dsl_todo_notes/sample.c             |   3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |   3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |   3 +
 tests/fixtures/dsl_todo_notes/sample.java          |   3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |   3 +
 tests/fixtures/dsl_todo_notes/sample.py            |   9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |   3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |   3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |   3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |  14 +
 .../lang/csharp/combined_static_and_namespace.cs   |  16 +
 tests/fixtures/lang/csharp/directives.cs           |  44 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |  12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |  12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |  12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |  12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |  12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |  12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |  13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |  13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |  13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |  12 +
 .../fixtures/lang/csharp/nested_property_event.cs  |  37 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 .../lang/csharp/tests/malformed_results.xml        |   5 +
 .../fixtures/lang/csharp/tests/sample_results.trx  |  15 +
 .../lang/csharp/tests/sample_unity_results.xml     |   9 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |  20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |  21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |  18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 .../Assets/Editor/Editor.asmdef                    |   6 +
 .../Assets/Editor/Editor.asmdef.meta               |   2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |   2 +
 .../Assets/Runtime/Runtime.asmdef                  |   6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |   2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |   6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |   2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |   6 +
 .../Assets/Tests/Tests.asmdef.meta                 |   2 +
 .../unity_sample_asmdef/Packages/manifest.json     |   3 +
 .../ProjectSettings/ProjectVersion.txt             |   2 +
 tests/gates_suite/test_claim_lint.py               | 163 ++++
 tests/gates_suite/test_coverage.py                 | 132 ++-
 tests/gates_suite/test_fix_engine.py               | 123 +++
 tests/gates_suite/test_guard_closure.py            | 228 +++++
 tests/gates_suite/test_invariant.py                | 116 +++
 tests/test_check_gate_base.py                      |  54 ++
 tests/test_docenum_gate.py                         |  41 +
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 +
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 ++
 tests/test_lang.py                                 |  90 ++
 tests/test_lang_conformance_gate.py                |  81 +-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 ++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++--
 tests/test_tickets_migration.py                    | 121 ++-
 tests/test_tickets_parent.py                       | 208 +++++
 tests/test_tickets_registry_files.py               | 206 +++++
 tests/test_waive_gate.py                           | 145 ++++
 tests/ticket_land_suite/test_verify_intent.py      |  85 +-
 tests/unit/graph/test_dsl.py                       | 164 +++-
 tests/unit/graph/test_dsl_invariant_property.py    |  69 ++
 tests/unit/lang/test_csharp_directives.py          | 115 +++
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++
 tests/unit/strata/test_effects.py                  |  44 +
 tests/unit/strata/test_selfconform.py              | 460 +++++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 +--
 tests/unit/test_check_scoped_files.py              | 566 ++++++++++++
 tests/unit/test_check_skip_flag.py                 | 192 ++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 ++++
 tests/unit/test_cli_group_parity.py                | 220 +++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  60 +-
 tests/unit/test_doctor.py                          | 116 +++
 tests/unit/test_done_report_check_scope.py         | 177 ++++
 tests/unit/test_dotnet_runner.py                   | 194 +++++
 tests/unit/test_land_default_queue.py              | 128 +++
 tests/unit/test_land_in_progress_window.py         | 351 ++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 ++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 +++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++
 tests/unit/test_lifecycle_work_base.py             | 217 +++++
 tests/unit/test_pyproject_data_memoization.py      | 124 +++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 +++
 tests/unit/test_store_mode_memoization.py          | 110 +++
 tests/unit/test_support_csharp.py                  | 190 ++++
 tests/unit/test_suppress_worktree_path.py          |  87 ++
 tests/unit/test_ticket_cli_surface.py              | 182 ++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_unity_batchmode.py                 | 194 +++++
 tests/unit/test_xref.py                            | 118 +++
 tests/vet_suite/test_capability_registry_unity.py  | 130 +++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++
 tickets/T-1661/ticket.md                           |  23 +-
 tickets/T-1778/ticket.md                           |  17 +-
 tickets/T-1820/ticket.md                           |  17 +-
 tickets/T-1831/ticket.md                           |  17 +-
 tickets/T-2451/ticket.md                           |  17 +-
 tickets/T-2752/ticket.md                           |  17 +-
 tickets/T-2803/ticket.md                           |  17 +-
 tickets/T-2835/ticket.md                           |  17 +-
 tickets/T-2837/ticket.md                           |  17 +-
 tickets/T-2856/ticket.md                           |  17 +-
 tickets/T-2886/ticket.md                           |  17 +-
 tickets/T-2889/ticket.md                           |  23 +-
 tickets/T-2939/ticket.md                           |  17 +-
 tickets/T-2962/ticket.md                           |  17 +-
 tickets/T-2965/done-report.md                      | 149 ++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/done-report.md                      | 578 +++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  83 +-
 tickets/T-3053/ticket.md                           |  32 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  17 +-
 tickets/T-3082/ticket.md                           |  63 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  17 +-
 tickets/T-3127/ticket.md                           |  17 +-
 tickets/T-3193/ticket.md                           |  17 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  17 +-
 tickets/T-3232/done-report.md                      | 179 ++++
 tickets/T-3232/ticket.md                           |  88 +-
 tickets/T-3233/done-report.md                      | 606 +++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  24 +-
 tickets/T-3262/ticket.md                           |  17 +-
 tickets/T-3270/ticket.md                           |  17 +-
 tickets/T-3274/ticket.md                           |  16 +-
 tickets/T-3327/ticket.md                           |  17 +-
 tickets/T-3330/ticket.md                           |  17 +-
 tickets/T-3335/ticket.md                           |  17 +-
 tickets/T-3351/ticket.md                           |  17 +-
 tickets/T-3357/ticket.md                           |  17 +-
 tickets/T-3359/ticket.md                           |  17 +-
 tickets/T-3377/ticket.md                           |  17 +-
 tickets/T-3412/ticket.md                           |  34 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3611/ticket.md                           |   8 +-
 tickets/T-3612/done-report.md                      | 221 +++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 ++++-
 tickets/T-3614/ticket.md                           | 111 ++-
 tickets/T-3615/done-report.md                      |  33 +
 tickets/T-3615/ticket.md                           |  30 +-
 tickets/T-3620/ticket.md                           |  16 +-
 tickets/T-3646/ticket.md                           |  17 +-
 tickets/T-3659/ticket.md                           |  16 +-
 tickets/T-3660/ticket.md                           |  17 +-
 tickets/T-3677/ticket.md                           |  17 +-
 tickets/T-3714/ticket.md                           |  17 +-
 tickets/T-3716/ticket.md                           |  17 +-
 tickets/T-3728/ticket.md                           |  17 +-
 tickets/T-3729/ticket.md                           |  17 +-
 tickets/T-3739/ticket.md                           |  17 +-
 tickets/T-3758/ticket.md                           |  17 +-
 tickets/T-3783/ticket.md                           |  16 +-
 tickets/T-3789/ticket.md                           |  17 +-
 tickets/T-3802/ticket.md                           |  27 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3821/ticket.md                           |  46 +-
 tickets/T-3822/ticket.md                           |  45 +-
 tickets/T-3823/ticket.md                           |  45 +-
 tickets/T-3825/ticket.md                           |  49 +-
 tickets/T-3832/ticket.md                           |  44 +-
 tickets/T-3833/ticket.md                           |  44 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3854/ticket.md                           |  21 +-
 tickets/T-3856/done-report.md                      | 247 ++++++
 tickets/T-3856/ticket.md                           |  60 +-
 tickets/T-3859/ticket.md                           |  17 +-
 tickets/T-3867/ticket.md                           |  17 +-
 tickets/T-3882/ticket.md                           |  17 +-
 tickets/T-3883/ticket.md                           |  17 +-
 tickets/T-3896/ticket.md                           |  17 +-
 tickets/T-3899/ticket.md                           |  26 +
 tickets/T-3904/ticket.md                           |  17 +-
 tickets/T-3917/ticket.md                           |  17 +-
 tickets/T-3918/ticket.md                           |  16 +-
 tickets/T-3919/ticket.md                           |  17 +-
 tickets/T-3920/ticket.md                           |  87 +-
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3927/ticket.md                           |  21 +-
 tickets/T-3929/ticket.md                           |  21 +-
 tickets/T-3943/done-report.md                      | 626 ++++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3953/ticket.md                           |   9 +-
 tickets/T-3961/done-report.md                      | 701 +++++++++++++++
 tickets/T-3961/ticket.md                           |  47 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3964/ticket.md                           |  22 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |  19 +-
 tickets/T-3997/ticket.md                           |  25 +-
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4019/ticket.md                           |  11 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/done-report.md                      | 726 ++++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  57 +-
 tickets/T-4113/ticket.md                           |  58 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/done-report.md                      | 707 +++++++++++++++
 tickets/T-4116/ticket.md                           |  17 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4127/ticket.md                           |  55 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 ++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/done-report.md                      | 706 +++++++++++++++
 tickets/T-4221/ticket.md                           |  92 +-
 tickets/T-4230/done-report.md                      | 723 ++++++++++++++++
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4392/ticket.md                           |  11 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           | 242 +++++-
 tickets/T-4420/ticket.md                           | 382 +++++++-
 tickets/T-4421/ticket.md                           | 483 ++++++++++-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4447/ticket.md                           |  11 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 ++
 tickets/T-4492/done-report.md                      |  34 +
 tickets/T-4492/ticket.md                           |  67 ++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 +++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 +
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 ++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 +++++++++++++
 tickets/T-4503/ticket.md                           |  94 ++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/done-report.md                      | 793 +++++++++++++++++
 tickets/T-4507/ticket.md                           |  57 ++
 tickets/T-4508/done-report.md                      | 689 +++++++++++++++
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  48 +
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 ++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 +++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 ++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 ++++
 tickets/T-4517/ticket.md                           |  94 ++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/done-report.md                      | 869 +++++++++++++++++++
 tickets/T-4519/ticket.md                           |  79 ++
 tickets/T-4520/done-report.md                      | 163 ++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 +++++
 tickets/T-4521/ticket.md                           | 125 +++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/done-report.md                      | 209 +++++
 tickets/T-4524/ticket.md                           |  52 ++
 tickets/T-4526/ticket.md                           |  45 +
 tickets/T-4529/ticket.md                           |  76 ++
 tickets/T-4530/ticket.md                           |  64 ++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 +++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 ++
 tickets/T-4533/ticket.md                           |  35 +
 tickets/T-4534/ticket.md                           |  69 ++
 tickets/T-4535/done-report.md                      |  64 ++
 tickets/T-4535/ticket.md                           |  61 ++
 tickets/T-4536/done-report.md                      |  78 ++
 tickets/T-4536/ticket.md                           | 128 +++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 ++
 tickets/T-4547/done-report.md                      | 137 +++
 tickets/T-4547/ticket.md                           |  45 +
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 +++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 ++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++
 tickets/T-4556/ticket.md                           |  46 +
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 +
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/done-report.md                      | 665 ++++++++++++++
 tickets/T-4562/ticket.md                           |  54 ++
 tickets/T-4563/done-report.md                      | 556 ++++++++++++
 tickets/T-4563/ticket.md                           |  47 +
 tickets/T-4566/ticket.md                           | 154 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 +
 tickets/T-4572/ticket.md                           |  81 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  52 ++
 tickets/T-4579/done-report.md                      | 522 +++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 +
 tickets/T-4581/ticket.md                           |  47 +
 tickets/T-4582/done-report.md                      | 551 ++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 +++++++++++++
 tickets/T-4583/ticket.md                           |  87 ++
 tickets/T-4588/done-report.md                      | 715 +++++++++++++++
 tickets/T-4588/ticket.md                           |  67 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++
 tickets/T-4596/ticket.md                           |  43 +
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  46 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 +
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  82 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 +++++++++++++++++
 tickets/T-4607/ticket.md                           |  81 ++
 tickets/T-4608/ticket.md                           |  41 +
 tickets/T-4609/ticket.md                           |  27 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           | 116 +++
 tickets/T-4615/ticket.md                           | 105 +++
 tickets/T-4616/ticket.md                           |  43 +
 tickets/T-4617/ticket.md                           |  27 +
 tickets/T-4618/ticket.md                           |  52 ++
 tickets/T-4619/ticket.md                           |  64 ++
 tickets/T-4620/ticket.md                           |  52 ++
 tickets/T-4622/ticket.md                           | 107 +++
 tickets/T-4623/ticket.md                           |  64 ++
 tickets/T-4624/ticket.md                           |  52 ++
 tickets/T-4625/ticket.md                           |  43 +
 tickets/T-4626/ticket.md                           |  27 +
 tickets/T-4627/ticket.md                           |  52 ++
 tickets/T-4628/ticket.md                           |  53 ++
 tickets/T-4629/ticket.md                           |  46 +
 tickets/T-4630/ticket.md                           |  54 ++
 tickets/T-4631/ticket.md                           |  71 ++
 tickets/T-4632/ticket.md                           |  41 +
 tickets/T-4633/done-report.md                      | 743 ++++++++++++++++
 tickets/T-4633/ticket.md                           |  86 ++
 tickets/T-4634/done-report.md                      | 851 ++++++++++++++++++
 tickets/T-4634/ticket.md                           |  54 ++
 tickets/T-4635/ticket.md                           |  30 +
 tickets/T-4640/ticket.md                           |  30 +
 tickets/T-4641/ticket.md                           |  29 +
 tickets/T-4642/done-report.md                      | 671 ++++++++++++++
 tickets/T-4642/ticket.md                           |  52 ++
 tickets/T-4643/ticket.md                           |  29 +
 tickets/T-4644/ticket.md                           |  29 +
 tickets/T-4645/ticket.md                           |  59 ++
 tickets/T-4646/ticket.md                           |  43 +
 tickets/T-4647/ticket.md                           |  49 ++
 tickets/T-4648/ticket.md                           |  28 +
 tickets/T-4649/done-report.md                      | 888 +++++++++++++++++++
 tickets/T-4649/ticket.md                           | 105 +++
 tickets/T-4650/done-report.md                      | 961 +++++++++++++++++++++
 tickets/T-4650/ticket.md                           | 166 ++++
 tickets/T-4651/ticket.md                           |  55 ++
 tickets/T-4652/ticket.md                           |  46 +
 tickets/T-4653/ticket.md                           |  44 +
 tickets/T-4654/ticket.md                           |  48 +
 tickets/T-4655/ticket.md                           |  43 +
 tickets/T-4656/ticket.md                           |  47 +
 tickets/T-4657/ticket.md                           |  74 ++
 tickets/T-4658/ticket.md                           |  56 ++
 tickets/T-4659/ticket.md                           |  61 ++
 tickets/T-4660/ticket.md                           |  60 ++
 tickets/T-4661/ticket.md                           |  66 ++
 tickets/T-4662/ticket.md                           |  85 ++
 tickets/T-4663/ticket.md                           |  73 ++
 tickets/T-4664/ticket.md                           |  68 ++
 tickets/T-4665/ticket.md                           |  69 ++
 tickets/T-4666/ticket.md                           |  72 ++
 tickets/T-4667/ticket.md                           |  63 ++
 tickets/T-4668/ticket.md                           |  93 ++
 tickets/T-4669/ticket.md                           |  89 ++
 tickets/T-4670/ticket.md                           |  86 ++
 tickets/T-4671/ticket.md                           | 105 +++
 tickets/T-4672/ticket.md                           |  89 ++
 tickets/T-4673/ticket.md                           |  83 ++
 tickets/T-4674/ticket.md                           |  77 ++
 tickets/T-4675/ticket.md                           | 104 +++
 tickets/T-4676/ticket.md                           |  85 ++
 tickets/T-4677/ticket.md                           |  90 ++
 tickets/T-4678/ticket.md                           | 110 +++
 tickets/T-4679/ticket.md                           |  29 +
 tickets/T-4680/ticket.md                           |  95 ++
 tickets/T-4681/ticket.md                           |  96 ++
 tickets/T-4684/ticket.md                           |  62 ++
 tickets/T-4685/ticket.md                           |  52 ++
 tickets/T-draft-31fbe483/ticket.md                 |  34 +
 tickets/T-draft-5658939f/ticket.md                 |  53 ++
 tickets/T-draft-8c1c8d09/ticket.md                 |  35 +
 tickets/T-4686/ticket.md                 |  33 +
 tickets/archive/T-0090/ticket.md                   |  18 +
 tickets/archive/T-0240/ticket.md                   |  18 +
 tickets/archive/T-0292/ticket.md                   |  18 +
 tickets/archive/T-0336/ticket.md                   |  18 +
 tickets/archive/T-0364/ticket.md                   |  24 +
 tickets/archive/T-0403/ticket.md                   |  18 +
 tickets/archive/T-0470/ticket.md                   |  17 +
 tickets/archive/T-0525/ticket.md                   |  18 +
 tickets/archive/T-0553/ticket.md                   |  18 +
 tickets/archive/T-0557/ticket.md                   |  18 +
 tickets/archive/T-0730/ticket.md                   |  18 +
 tickets/archive/T-0814/ticket.md                   |  26 +
 tickets/archive/T-1148/ticket.md                   |  18 +
 tickets/archive/T-1265/ticket.md                   |  18 +
 tickets/archive/T-1266/ticket.md                   |  18 +
 tickets/archive/T-1402/ticket.md                   |  18 +
 tickets/archive/T-1651/ticket.md                   |  11 +-
 tickets/archive/T-1746/ticket.md                   |  94 +-
 tickets/archive/T-2314/ticket.md                   |   9 +
 tickets/archive/T-2338/ticket.md                   |   9 +
 tickets/archive/T-2438/ticket.md                   |   9 +
 tickets/archive/T-2454/ticket.md                   |   9 +
 tickets/archive/T-2688/ticket.md                   |   9 +
 tickets/archive/T-2710/ticket.md                   |   9 +
 tickets/archive/T-3128/ticket.md                   |  28 +
 tickets/archive/T-3255/ticket.md                   |   9 +
 tickets/archive/T-3664/ticket.md                   |  11 +-
 tickets/archive/T-3665/ticket.md                   |  10 +-
 tickets/archive/T-3667/ticket.md                   |  11 +-
 uv.lock                                            |   2 +-
 708 files changed, 63180 insertions(+), 2184 deletions(-)
```

### Evidence
- `tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_memoized` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_invalidates_on_mtime_change` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_missing_pyproject_returns_none_and_stays_cached` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_scales_across_many_candidates_and_leases` (pytest node id, verified passing when recorded)
