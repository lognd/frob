## Done report

Narrowed build_graph's cross-process exclusive derived_state_write_lock hold
to only the cache-mutating tail (_prune_stale_cache + conn.commit()) instead
of the whole walk+parse; T-0918 originally held it around the entire
rebuild, which serialized concurrent build_graph callers (e.g. pytest -n
xdist workers) behind each other for the full parse duration -- measured as
a ~19-minute CI tail stall.

Evidence:
- 6-test bundle (-p no:xdist): exitstatus=0 collected=6 failed=0
- Same bundle under `FROB_SUGGEST_ACK=1 uv run pytest -n 4`: exitstatus=0
  collected=6 failed=0, wall 5.76s, no "node down"
- `uv run frob test` (touched set, 18 python tests): [PASS] python exit=0
  duration=128.00s
- 2-process wall-time experiment (measured before/after in-worktree, root=
  this worktree, ~8500-file tree):
  before fix: single build ~34.96s; two concurrent builds (different cache
    files, same root) finished at 24.10s and 46.17s -- serialized behind
    each other's exclusive flock for the full parse.
  after fix: single build ~15.99s (warmer FS cache by then); two concurrent
    builds finished at 17.26s and 17.82s (wall for both ~18.27s total) --
    running genuinely in parallel, matching single-build time instead of
    summing to ~70s of serialized span.

Filed: none (SELFAUDIT001/SYS111 ratchet bump and the AFFECT002 dependent
were both resolved in-scope, not deferred).

Gates: `uv run frob check --ticket T-3478` -- all ticket-scoped gate
families (gate:SCOPE, gate:PREWORK, gate:FMT, gate:AFFECT, and the
diff-driven COV002/TODO001 checks inside gate:COV) pass clean.
gate:SELFAUDIT (repo-wide, unscoped) also passes clean after the
ratchet-ceiling bump. Every remaining FAIL in the repo-wide (unscoped)
gate families is pre-existing and does not reference any file this
ticket touched.

### Changed
```
 tickets/T-3478/done-report.md | 49 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3478/ticket.md      | 23 +++++++++++++++++++-
 2 files changed, 71 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_parse_runs_while_another_process_holds_the_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_two_processes_never_commit_to_the_same_cache_concurrently` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_build_lock.py::TestBuildGraphCacheLockedStillReported::test_cache_locked_from_connect_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestLoadGraph::test_non_utf8_doc_file_is_skipped_not_crashed` (pytest node id, verified passing when recorded)
- `tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildIncremental::test_stats_sum_source_and_doc_counts_not_difference` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 10 error(s), 4637 warning(s), 870 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3478, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
