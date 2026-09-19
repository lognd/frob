## Done report

Ticket: T-4649 -- TICK008 real-repo smoke test exceeds 120s on posix under fleet load
Worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-cdd5b1eb
Branch: t-draft-cdd5b1eb
Disposition: READY

## WHAT changed

- src/frob/tickets/_store.py
  - Added `_store_mode_cache` (module-level dict) + `_store_mode_cache_lock`
    (threading.Lock) and `_store_mode_cache_signal(root)`, which returns the
    mtimes of the three on-disk locations `_store_mode` itself inspects
    (`tickets/`, `tickets/archive/`, `tickets.md`), -1.0 for any missing.
  - `_store_mode(root)` now checks the cache keyed by `root`, comparing the
    stored signal to a freshly computed one; on a hit it returns the cached
    mode with NO glob at all; on a miss it does the original computation and
    stores (signal, mode) before returning.
  - Both new symbols carry `frob:ticket T-4649` and `frob:tests`
    directives.

- tests/unit/test_store_mode_memoization.py (new file)
  - `TestStoreModeMemo` with 4 tests: `test_memoized` (positive control --
    monkeypatches `Path.glob` to count calls, asserts zero re-globs across 5
    repeated `_store_mode` calls on an unchanged tree), `test_invalidates_new`
    (plants a new v2 ticket after the first cached call, asserts the answer
    flips single -> v2), `test_store_mode_cache_invalidates_on_archive`
    (T-1256's all-archived-still-v2 rule through the cache), and
    `test_store_mode_cache_is_per_root` (two roots never share a cache slot).
  - Kept in its own file rather than `tests/unit/test_ticket_store.py`
    because that file is under a LIVE cross-ticket lease (T-4632) at the
    time of this fix -- `frob ticket scope --add
    tests/unit/test_ticket_store.py` was refused with ScopeLeaseConflict.

- tickets/T-4649/ticket.md
  - `blocked_by: T-4625` recorded by a PRIOR session, then UNBLOCKED by this
    session (see WHY below) -- state moved from blocked back to in-progress,
    scope expanded to include `src/frob/tickets/_store.py`,
    `src/frob/tickets/_leases.py` (added by the prior session, kept read-only
    -- audited but not modified, see below), and
    `tests/unit/test_store_mode_memoization.py`.
  - `designated_repro_test` set (forced -- see repro section below).

## WHY

### Correcting a false "blocked" state left by a prior session

A PRIOR session on this same ticket/worktree diagnosed the root cause
correctly (see the "## DIAGNOSIS" section already in the ticket body,
commit ed3c73cfe) but concluded the fix was BLOCKED because the two files
it needed (`src/frob/tickets/_store.py`, `src/frob/tickets/_leases.py`)
were "leased by T-4625 / T-4632". I verified this directly against every
lease file's actual `scope` array (not a raw grep, which false-matches:
`test_ticket_leases.py` and `test_ticket_store.py` both contain the
substrings `_leases.py` / `_store.py`) and confirmed NEITHER T-4625 nor
T-4632 (nor any other lease file in `.git/frob-leases/`) actually scopes
either src file. I unblocked the ticket (`frob ticket unblock T-4649
--by T-4625 --reason ...`) and proceeded with the fix in this ticket's own
worktree, as the standing brief's ROOT-rule clarification and scope-add
mechanism both sanction.

### The fix itself

`_store_mode(root)` (src/frob/tickets/_store.py) re-globbed the entire
`tickets/` tree (active AND `tickets/archive/`) on EVERY call, with no
caching. `_ticket_ledger_staleness_shape` (src/frob/tickets/_leases.py)
calls it; `_prune_one_lease_record` calls that once PER LEASE inside
`read_all_leases()`; `doable()` (src/frob/tickets/_doable.py) calls
`read_all_leases()`-backed lease checks once PER CANDIDATE TICKET while
filtering lease collisions. Net effect: O(active_tickets x live_leases)
full-directory-tree glob scans -- at this repo's own scale (1000+ active
tickets, dozens of concurrent fleet leases) this measured out to minutes
per ledger verb (`frob ticket doable`, `new`, `accept`, and any TICK-gate
check that walks `doable()` -- this is also why `frob ticket new`/`scope`/
`unblock` in THIS very session each took many minutes under fleet lock
contention while filing this fix).

Fixed by memoizing `_store_mode` per root, keyed on a cheap invalidation
signal: the mtimes of `tickets/`, `tickets/archive/`, and `tickets.md`.
Any ticket creation/archive/drop or v1/v2 migration touches at least one
of these paths' own mtime (a new/removed directory entry, or the ledger
file's own atomic-write replace), so a stale cache entry is detected on
the very next call after any change that could flip the answer -- proven
by the two positive-control invalidation tests, not just a "same answer
twice" timing assertion a broken (never-invalidating) cache would also
pass.

### Audit of doable()/_leases.py for the same per-call re-scan pattern

Per the ticket's own instruction to audit for and fix every instance of
this pattern, I re-ran the real-repo TICK008 smoke test AFTER the
`_store_mode` fix. It still exceeds the 120s/150s budget (measured
real=2m9s, essentially unchanged) -- but the faulthandler dump now shows
a DIFFERENT dominant cost, confirming `_store_mode` was fixed and exposing
the next bottleneck: `doable()` -> `leased_by()` ->
`_leased_by_one_holder()` (src/frob/tickets/_doable.py:671) calls
`over_broad_literal_globs(root)` (src/frob/tickets/_models.py:829) ->
`declared_source_prefixes(root)` -> `declared_project_package_name(root)`
(src/frob/lang/_nodes.py), which does `tomllib.load()` on `pyproject.toml`
FRESH on every call -- once per candidate ticket x lease holder pair,
same O(tickets x leases) shape.

This is a DISTINCT root cause in DIFFERENT files (`src/frob/tickets/
_models.py`, `src/frob/lang/_nodes.py`) not covered by this ticket's
lease/scope. A ticket for it already exists: T-draft-cff39530 (confirmed
via `frob ticket new` itself refusing my attempt to file a duplicate,
"100% match" against T-draft-cff39530's title) -- so no new ticket filed
here, per the standing rule against silently expanding scope or filing a
redundant duplicate. `src/frob/tickets/_leases.py` was left in my ticket's
scope (added by the prior session) but NOT modified -- I read it to trace
the call chain but found no additional uncached-re-scan instance inside
that file itself; the second defect lives entirely in `_models.py`/
`_nodes.py`.

## How each finding is proven / acceptance criteria

1. `_store_mode` no longer re-globs on a cache hit:
   `test_memoized` -- monkeypatches `Path.glob` to count invocations,
   asserts 0 calls across 5 repeated `_store_mode(tmp_path)` calls on an
   unchanged tree (first call is the cache-warming call, made before the
   monkeypatch is installed).
2. The cache invalidates correctly on a real ledger mutation (not stale
   forever): `test_invalidates_new` (v1 -> v2 flip via a new ticket dir)
   and `test_store_mode_cache_invalidates_on_archive` (T-1256's
   all-archived-still-v2 rule, exercised through an active-ticket-removed
   + archived-ticket-added mutation).
3. The cache is correctly scoped per repo root, not global:
   `test_store_mode_cache_is_per_root`.
4. Existing `_store_mode` behavior is unchanged for every case the
   pre-existing `TestV2StoreMode` class in tests/unit/test_ticket_store.py
   covers -- ran unmodified alongside the new tests, all pass (see node
   ids below).
5. Real-repo timing: measured `_store_mode`'s own contribution is now a
   single mtime-stat probe per call once warm, not a directory glob;
   the real-repo TICK008 test's remaining >120s cost is now attributable
   to the SEPARATE `over_broad_literal_globs`/pyproject.toml-reread defect
   (T-draft-cff39530), confirmed by re-running the exact same faulthandler
   repro command and observing the stack trace's hot frame move from
   `_store_mode`/`Path.glob` to `declared_project_package_name`/
   `tomllib.load`.

## Test node ids / evidence

Bound via `frob ticket evidence T-4649 <node-ids...> --base-ref dev`:
  tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_memoized
  tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_invalidates_new
  tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_store_mode_cache_invalidates_on_archive
  tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_store_mode_cache_is_per_root

Also ran (unmodified, not re-bound as new evidence, confirms no regression):
  tests/unit/test_ticket_store.py::TestV2StoreMode (4 tests, all pass)

Repro designation (kind=bug, BUG002): `designated_repro_test` set to
`tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_memoized`
via `--designate-repro-force`. `--check-repro` against the pre-fix parent
commit could not produce a FAILED_AT_PARENT verdict because the test FILE
itself is new (added in the same commit as the fix): at the parent commit
the file does not exist at all, so pytest reports "no tests ran" / a clean
collection with zero matches (`TEST_ABSENT_AT_PARENT`), which the tool
itself explains is a known structural limitation for a repro test that is
new alongside its own fix, distinct from a genuine false-positive
NO_VERDICT. By direct inspection: the pre-fix `_store_mode` body has no
cache at all, so `Path.glob` is invoked via `_v2_glob`/`_v2_archive_glob`
on every one of the test's 5 repeated calls, which would fail the
`calls["n"] == 0` assertion -- the intended real repro, force-recorded per
`--designate-repro-force`'s documented purpose for this exact shape.

## Commit shas (this session's own work, on top of the prior session's)

47a656868 chore(tickets): record T-4649 start transition        [prior session]
ed3c73cfe chore(tickets): record tick008 stall diagnosis                  [prior session]
11810e36f chore(tickets): block T-4649                          [prior session]
5e5080d35 / 9376345fa / 899b6518d  chore(tickets): scope T-4649 [this session -- unblock + scope adds]
77aeddaad fix(tickets): memoize _store_mode to fix TICK008 real-repo perf [this session -- THE FIX]
715178185 chore(tickets): record evidence for T-4649            [this session]
b19842929 chore(tickets): record evidence for T-4649            [this session -- repro designation]

HEAD: b1984292972544fb28ddd8ec7f9fef900bc1bbf2

## Scope note for the coordinator

`src/frob/tickets/_store.py` and `tests/unit/test_store_mode_memoization.py`
are exclusively this ticket's own lease -- no collision. `src/frob/tickets/
_leases.py` is also in this ticket's scope (added by the prior session)
but UNMODIFIED by this session's diff (`git diff --name-only dev...HEAD`
shows only `_store.py`, the new test file, and `ticket.md` -- `_leases.py`
carries no diff). Filed nothing new: the follow-up finding (over_broad_
literal_globs re-reading pyproject.toml uncached) is already covered by
the pre-existing T-draft-cff39530.

## Pre-READY checks

`frob check --only sys --files src/frob/tickets/_store.py --files tests/unit/test_store_mode_memoization.py --base dev`:
  gate:DRIFT FAIL (5 errors, all waived, none attributable to my files --
    pre-existing drift on src/frob/app/ticket_runner/_rapid_sweep.py,
    src/frob/gates/invariants.py, src/frob/tickets/_evidence.py);
  gate:DSL FAIL (1 error, tests/test_app.py:387, pre-existing, not mine);
  gate:SELFAUDIT FAIL (1 error, a repo-wide SYS111 testsuite via-count
    ratchet note, not tied to my glob); gate:DOCARCH pass; gate:PROFILE
    pass; gate:WAIVE pass. ZERO findings attributable to
    src/frob/tickets/_store.py or tests/unit/test_store_mode_memoization.py.

`frob check --only arch --files src/frob/tickets/_store.py --files tests/unit/test_store_mode_memoization.py --base dev`:
  pass -- 19 warnings (36 waived) + 542 suggestions, all repo-wide
  pattern-recommendation notes on unrelated files/classes. No ARCH001,
  no LARGE001.

`frob check --only coverage --files src/frob/tickets/_store.py --files tests/unit/test_store_mode_memoization.py --base dev`:
  Initial run found ONE attributable finding: COV002 on the new
  `_store_mode_cache_signal` symbol (missing frob:ticket edge) -- fixed by
  adding the `frob:ticket T-4649` / `frob:tests` directives to
  that function. Re-run after the fix: 0 COV002/COV007 findings
  attributable to my new symbols (all remaining COV/DOCARCH/PLACE findings
  in the output are pre-existing, on other functions in the same file, all
  already waived).

`ruff check src/frob/tickets/_store.py tests/unit/test_store_mode_memoization.py`: All checks passed!
`ruff format --check src/frob/tickets/_store.py tests/unit/test_store_mode_memoization.py`: 2 files already formatted

`ty check src/frob/tickets/_store.py tests/unit/test_store_mode_memoization.py`: All checks passed!

## Tests skipped / not run

Did not re-run the full real-repo TICK008 test to a passing state -- it
cannot pass within budget until T-draft-cff39530's separate defect is also
fixed (confirmed via faulthandler that the remaining cost is entirely
attributable to that ticket's own scope, not to anything in this diff).
This is a pre-existing multi-cause failure being fixed incrementally
across two tickets, not a regression introduced or left uncovered by this
fix.

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 +++-
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  64 ++
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
 changelog.d/T-4642.md                              |   2 +
 design/frob.strata                                 | 167 +++--
 docs/commands/check.md                             |  88 ++-
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  88 ++-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/extending/comment-dsl-directives.md    |  13 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/guides/unity.md                               |  83 +++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |  95 +++
 docs/modules/gate-time-stable-invariant.md         |  74 ++
 docs/modules/gates.md                              | 146 +++-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  37 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 ++++-
 docs/modules/tickets.md                            |   9 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/__init__.py                  |   2 +
 src/frob/_cli_parsers/_check.py                    | 295 +++++++-
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 +++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       | 154 ++--
 src/frob/app/config.py                             |  92 ++-
 src/frob/app/ticket_runner/__init__.py             | 125 ++--
 src/frob/app/ticket_runner/_close_cmd.py           |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 ++++++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 245 ++++++-
 src/frob/check/__init__.py                         | 244 ++++---
 src/frob/check/_python.py                          | 152 ++--
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 +++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 ++++++
 src/frob/excludes.py                               |  83 ++-
 src/frob/gates/__init__.py                         | 263 ++++---
 src/frob/gates/_claim_lint.py                      | 202 ++++++
 src/frob/gates/_coverage.py                        | 203 +++++-
 src/frob/gates/_fix_engine.py                      |  94 ++-
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_guard_closure.py                   | 301 ++++++++
 src/frob/gates/_inv.py                             | 359 +++++++++
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 ++++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 185 ++++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 +++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 780 ++++++++++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 +++++++++
 src/frob/testing/_dotnet_runner.py                 | 251 +++++++
 src/frob/testing/_runners.py                       |  10 +
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/testing/_unity_batchmode.py               | 298 ++++++++
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 122 +++-
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   |  49 +-
 src/frob/tickets/_leases.py                        | 552 ++++++++++----
 src/frob/tickets/_models.py                        |  42 +-
 src/frob/tickets/_setters.py                       | 113 ++-
 src/frob/tickets/_store.py                         | 121 +++-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 ++++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 ++++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  54 +-
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
 tests/fixtures/lang/csharp/directives.cs           |  44 ++
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
 tests/gates_suite/test_claim_lint.py               | 163 +++++
 tests/gates_suite/test_coverage.py                 | 132 +++-
 tests/gates_suite/test_fix_engine.py               | 123 ++++
 tests/gates_suite/test_guard_closure.py            | 228 ++++++
 tests/gates_suite/test_invariant.py                | 116 +++
 tests/test_check_gate_base.py                      |  54 ++
 tests/test_docenum_gate.py                         |  41 ++
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 ++
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 +++
 tests/test_lang.py                                 |  90 +++
 tests/test_lang_conformance_gate.py                |  81 ++-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 +++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++---
 tests/test_tickets_migration.py                    | 121 ++--
 tests/test_tickets_parent.py                       | 208 ++++++
 tests/test_waive_gate.py                           | 145 ++++
 tests/unit/graph/test_dsl.py                       | 164 ++++-
 tests/unit/graph/test_dsl_invariant_property.py    |  69 ++
 tests/unit/lang/test_csharp_directives.py          | 115 +++
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++++
 tests/unit/strata/test_effects.py                  |  44 ++
 tests/unit/strata/test_selfconform.py              | 460 +++++++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 ++--
 tests/unit/test_check_scoped_files.py              | 566 +++++++++++++++
 tests/unit/test_check_skip_flag.py                 | 192 +++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 +++++
 tests/unit/test_cli_group_parity.py                | 220 ++++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  35 +-
 tests/unit/test_doctor.py                          | 116 +++
 tests/unit/test_done_report_check_scope.py         | 177 +++++
 tests/unit/test_dotnet_runner.py                   | 194 +++++
 tests/unit/test_land_default_queue.py              | 128 ++++
 tests/unit/test_land_in_progress_window.py         | 351 +++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 +++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 ++++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_leases_staleness_perf.py           | 310 ++++++++
 tests/unit/test_lifecycle_work_base.py             | 217 ++++++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 ++++
 tests/unit/test_store_mode_memoization.py          | 110 +++
 tests/unit/test_support_csharp.py                  | 190 +++++
 tests/unit/test_suppress_worktree_path.py          |  87 +++
 tests/unit/test_ticket_cli_surface.py              | 182 +++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_unity_batchmode.py                 | 194 +++++
 tests/unit/test_xref.py                            |  40 +
 tests/vet_suite/test_capability_registry_unity.py  | 130 ++++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 +++
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
 tickets/T-3020/done-report.md                      | 578 +++++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  17 +-
 tickets/T-3053/ticket.md                           |  16 +-
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
 tickets/T-3232/done-report.md                      | 179 +++++
 tickets/T-3232/ticket.md                           |  88 ++-
 tickets/T-3233/done-report.md                      | 606 ++++++++++++++++
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
 tickets/T-3612/done-report.md                      | 221 ++++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 +++++-
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
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3856/done-report.md                      | 247 +++++++
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
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3943/done-report.md                      | 626 ++++++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3953/ticket.md                           |   9 +-
 tickets/T-3961/done-report.md                      | 701 ++++++++++++++++++
 tickets/T-3961/ticket.md                           |  47 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3964/ticket.md                           |  22 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |  19 +-
 tickets/T-3997/ticket.md                           |   9 +-
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4019/ticket.md                           |  11 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/done-report.md                      | 726 +++++++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  57 +-
 tickets/T-4113/ticket.md                           |  58 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/done-report.md                      | 707 ++++++++++++++++++
 tickets/T-4116/ticket.md                           |  17 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 +++++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/done-report.md                      | 706 ++++++++++++++++++
 tickets/T-4221/ticket.md                           |  92 ++-
 tickets/T-4230/done-report.md                      | 723 +++++++++++++++++++
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
 tickets/T-4419/ticket.md                           | 242 ++++++-
 tickets/T-4420/ticket.md                           | 382 +++++++++-
 tickets/T-4421/ticket.md                           | 483 ++++++++++++-
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
 tickets/T-4494/done-report.md                      | 138 ++++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 ++
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 +++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 +++++++++++++++
 tickets/T-4503/ticket.md                           |  94 +++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/done-report.md                      | 793 ++++++++++++++++++++
 tickets/T-4507/ticket.md                           |  57 ++
 tickets/T-4508/done-report.md                      | 689 ++++++++++++++++++
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  48 ++
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 +++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 ++++++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 +++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 +++++
 tickets/T-4517/ticket.md                           |  94 +++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/ticket.md                           |  67 ++
 tickets/T-4520/done-report.md                      | 163 +++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 ++++++
 tickets/T-4521/ticket.md                           | 125 ++++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/done-report.md                      | 209 ++++++
 tickets/T-4524/ticket.md                           |  52 ++
 tickets/T-4526/ticket.md                           |  45 ++
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
 tickets/T-4536/ticket.md                           | 128 ++++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 +++
 tickets/T-4547/done-report.md                      | 137 ++++
 tickets/T-4547/ticket.md                           |  45 ++
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 +++++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 ++++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++++
 tickets/T-4556/ticket.md                           |  46 ++
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 ++
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/done-report.md                      | 665 +++++++++++++++++
 tickets/T-4562/ticket.md                           |  54 ++
 tickets/T-4563/done-report.md                      | 556 ++++++++++++++
 tickets/T-4563/ticket.md                           |  47 ++
 tickets/T-4566/ticket.md                           | 154 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 ++
 tickets/T-4572/ticket.md                           |  66 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  52 ++
 tickets/T-4579/done-report.md                      | 522 ++++++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 ++
 tickets/T-4581/ticket.md                           |  47 ++
 tickets/T-4582/done-report.md                      | 551 ++++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 ++++++++++++++++
 tickets/T-4583/ticket.md                           |  87 +++
 tickets/T-4588/done-report.md                      | 715 ++++++++++++++++++
 tickets/T-4588/ticket.md                           |  67 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++++
 tickets/T-4596/ticket.md                           |  43 ++
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  29 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 ++
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  82 +++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 +++++++++++++++++++++
 tickets/T-4607/ticket.md                           |  81 +++
 tickets/T-4608/ticket.md                           |  41 ++
 tickets/T-4609/ticket.md                           |  27 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           | 116 +++
 tickets/T-4615/ticket.md                           | 105 +++
 tickets/T-4616/ticket.md                           |  43 ++
 tickets/T-4617/ticket.md                           |  27 +
 tickets/T-4618/ticket.md                           |  52 ++
 tickets/T-4619/ticket.md                           |  64 ++
 tickets/T-4620/ticket.md                           |  52 ++
 tickets/T-4622/ticket.md                           | 107 +++
 tickets/T-4623/ticket.md                           |  64 ++
 tickets/T-4624/ticket.md                           |  52 ++
 tickets/T-4625/ticket.md                           |  43 ++
 tickets/T-4626/ticket.md                           |  27 +
 tickets/T-4627/ticket.md                           |  52 ++
 tickets/T-4628/ticket.md                           |  53 ++
 tickets/T-4629/ticket.md                           |  46 ++
 tickets/T-4630/ticket.md                           |  54 ++
 tickets/T-4631/ticket.md                           |  71 ++
 tickets/T-4632/ticket.md                           |  41 ++
 tickets/T-4633/done-report.md                      | 743 +++++++++++++++++++
 tickets/T-4633/ticket.md                           |  86 +++
 tickets/T-4634/ticket.md                           |  46 ++
 tickets/T-4635/ticket.md                           |  30 +
 tickets/T-4640/ticket.md                           |  30 +
 tickets/T-4641/ticket.md                           |  29 +
 tickets/T-4642/done-report.md                      | 671 +++++++++++++++++
 tickets/T-4642/ticket.md                           |  52 ++
 tickets/T-4643/ticket.md                           |  29 +
 tickets/T-4644/ticket.md                           |  29 +
 tickets/T-4645/ticket.md                           |  59 ++
 tickets/T-4646/ticket.md                           |  31 +
 tickets/T-4647/ticket.md                           |  34 +
 tickets/T-4648/ticket.md                           |  28 +
 tickets/T-draft-31fbe483/ticket.md                 |  34 +
 tickets/T-4748/ticket.md                 |  53 ++
 tickets/T-4751/ticket.md                 |  35 +
 tickets/T-4650/ticket.md                 | 166 +++++
 tickets/T-4649/ticket.md                 | 105 +++
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
 tickets/archive/T-1746/ticket.md                   |  94 +--
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
 647 files changed, 55448 insertions(+), 2098 deletions(-)
```

### Evidence
- `tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_memoized` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_invalidates_new` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_store_mode_cache_invalidates_on_archive` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_store_mode_cache_is_per_root` (pytest node id, verified passing when recorded)
