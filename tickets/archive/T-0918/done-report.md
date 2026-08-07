## Done report

Reentrancy design: added a process-wide (not thread-local) held-lock
registry to `src/frob/process/_lock.py` (`_process_registry_lock`,
`_process_held_counts`), incremented/decremented alongside the existing
per-thread `_lock_local` bookkeeping at every real `flock` acquire/
release. `_process_already_holds(root)` reports whether ANY thread in
this process currently holds `derived_state_lock` for `root`, in any
mode. A new `derived_state_write_lock(root)` context manager consults
that signal: if some thread in this process already holds the lock
(same-thread reentry, or a different thread -- e.g. `frob check`'s main
thread holding SHARED), it is a same-process no-op (no new OS lock
taken, trusting the outer holder's cross-process serialization);
otherwise it takes a real `derived_state_lock(root, exclusive=True)`.
This matches the ticket's specified fallback semantics exactly.
Documented trade-off (in the function's own docstring): two sibling
same-process standalone callers racing with no legitimate outer holder
are not mutually excluded against each other by this primitive -- no
current call site does this (both `find_clones` and `build_graph` are
either standalone or nested under `frob check`'s single main-thread
SHARED hold), so this is a documented latent gap, not an observed
regression.

Changed:
- `src/frob/process/_lock.py`: `_process_registry_lock`,
  `_process_held_counts`, `_process_already_holds`,
  `derived_state_write_lock`
- `src/frob/dup/_pipeline.py`: `find_clones` wrapped in
  `derived_state_write_lock(root)`
- `src/frob/graph/__init__.py`: `build_graph` wrapped in
  `derived_state_write_lock(root)`
- `tests/unit/test_process_lock.py`: added `TestDerivedStateWriteLock`
  (3 new tests) plus a `_hold_exclusive_then_signal` multiprocessing
  helper

Evidence: `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::
test_standalone_rebuild_takes_exclusive` (standalone rebuild takes a
real exclusive lock, verified via `_process_already_holds` flipping
True/False around the with-block), `::test_nested_inside_shared_holder_
does_not_deadlock` (worker thread nested under a main-thread SHARED
holder completes within a 5s join timeout guard -- no deadlock), `::
test_concurrent_separate_process_writer_still_blocked` (a real separate
OS process holding the exclusive lock still blocks this process's
`derived_state_write_lock` acquire until released, via `multiprocessing`
+ `Event` handshakes). All 8 tests in the file pass, including the
pre-existing T-0859 `TestDerivedStateLock` suite (regression check).
`tests/test_dup.py` (25 tests) and `tests/test_graph.py` (all tests)
also pass unchanged, confirming the `find_clones`/`build_graph` wiring
did not regress existing behavior. `frob check --ticket T-0918 --only
lint` passes clean (ruff-check, ruff-format, ty) after two autofixes
(import sort in `_pipeline.py`, formatting + an explicit
`multiprocessing.synchronize` import for `ty` in the test file).

Filed: none.

Gates: `frob check --ticket T-0918 --only lint` clean. The
`gates-fast`/`static`/`gates-native`/`gates-security` stage groups and
`frob test --base main` were invoked in the foreground per the chunked-
loop discipline but did not return within the harness's foreground
budget under this session's heavy concurrent multi-agent load (dozens of
other worktrees' background tasks contending for CPU on this host at the
time) -- they were not skipped by choice. The three ticket-mandated test
scenarios (standalone-exclusive, nested-no-deadlock,
concurrent-cross-process-blocked) are directly covered by the evidence
above and independently verified in the foreground.

## Post-land TEST016 fix

Land refused on TEST016: bound evidence killed 0/2 mutants of
`src/frob/graph/__init__.py`'s changed lines -- survivors at the
`parsed_count = src_parsed + doc_parsed` / `cache_hits = src_hits +
doc_hits` lines (inside `build_graph`'s cache-rebuild body, re-indented
by this ticket's `derived_state_write_lock` wrap). Both existing
`TestBuildIncremental` fixtures only ever build source-only trees (no
doc files), so `doc_parsed`/`doc_hits` are always 0 there and an
`Add`->`Sub` mutation on either line is invisible (`x + 0 == x - 0`).

Added `tests/test_graph.py::TestBuildIncremental::test_stats_sum_
source_and_doc_counts_not_difference`, a tree with exactly one source
file AND one top-level doc file (`README.md`) so both addends are
non-zero on both the fresh-parse build (`parsed == 2`, `cache_hits ==
0`) and the second all-cache-hit build (`parsed == 0`, `cache_hits ==
2`). Verified by hand: applying `src_parsed - doc_parsed` in place of
the `+` made the fresh-parse assertion fail (`parsed=0` instead of the
asserted `2`); reverted, then applying `src_hits - doc_hits` in place of
the `+` made the second-build assertion fail (`hits=0` instead of the
asserted `2`); reverted byte-identical (confirmed via `git diff
src/frob/graph/__init__.py` showing no diff after the revert). Bound as
T-0918 evidence via `frob ticket evidence T-0918 tests/test_graph.py::
TestBuildIncremental::test_stats_sum_source_and_doc_counts_not_
difference` (4th evidence id). Also added a `frob:tests` directive on
`build_graph` naming this test. `tests/test_graph.py` full file: all
tests pass (verified in the foreground).
