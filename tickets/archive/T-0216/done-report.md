## Done report

Root cause: `snapshot.malformed` (the `MalformedDirective` list backing the
`malformed=N` build-summary count in `frob.app.graph_runner._run_build`)
only ever got its per-file WARN log from `frob.graph.dsl.parse_directives`
-- which runs only on a fresh parse. On any build where the offending
file's content hash is unchanged (the common case: first build finds it,
every rebuild after is a cache hit), `_process_source_file` loads the
cached malformed rows straight from sqlite (`frob.graph.cache.load_file_data`)
with no log call at all, so `malformed=1` reappeared in the summary with no
way to trace it back to a file -- exactly the pilot P2 report, and it does
not self-heal on a cache flush/rebuild race the way I first assumed; it
reproduces deterministically on any cache-hit rebuild.

Fix: added `frob.graph._log_malformed_files`, called from
`_finalize_build` after `snapshot` is loaded from the cache -- this runs on
every `build_graph` call regardless of parse/cache-hit path, and WARN-logs
`malformed directive: <file>:<line>: <reason>` for every entry in
`snapshot.malformed`. This covers both the fresh-parse case (which also
still gets `dsl.parse_directives`'s own per-file warning, now redundant but
harmless) and the cache-hit case (which previously had none).

Changed:
- src/frob/graph/__init__.py::_log_malformed_files (new)
- src/frob/graph/__init__.py::_finalize_build (now calls it)
- tests/test_graph.py::TestMalformedFileVisibility (new regression class)

Evidence:
- tests/test_graph.py::TestMalformedFileVisibility::test_fresh_build_names_malformed_file -- PASSED (`uv run pytest tests/test_graph.py::TestMalformedFileVisibility -v`, 2 passed in 13.24s)
- tests/test_graph.py::TestMalformedFileVisibility::test_cache_hit_rebuild_still_names_malformed_file -- PASSED (same run; this is the regression test for the actual bug -- builds once, clears caplog, rebuilds against an unchanged cache, asserts the malformed file's path is still in WARN output and `stats.parsed == 0` to prove it went through the cache-hit path)
- Full `uv run pytest tests/test_graph.py -q`: all 66 collected tests pass (`......` x66, no failures)
- `ruff check src/frob/graph/__init__.py tests/test_graph.py`: All checks passed! (both bare `ruff` and `uv run ruff`, per playbook section 12)
- Manual repro before the fix (`frob graph build` on a two-file tmp tree, one file with a bad `frob:ticket` directive comment): first build printed `WARNING: bad.py: 1 malformed directive(s)`; second (cache-hit) build printed nothing but `malformed=1` in the summary. After the fix, both builds print `WARNING: malformed directive: bad.py:2: ...`.

Filed: none -- no out-of-scope work found.

Gates: `uv run frob check --delta --ticket T-0216 --json` -- gates tool
`0/5 new  0 violation(s), 27 waived` (baseline stamped via
`--stamp-baseline` before starting, which recorded 5 pre-existing waived
violations unrelated to this change; delta confirms zero new violations
introduced). Note: an earlier delta run flagged SCOPE001 on
`frob-core/Cargo.lock` / `strata-core/Cargo.lock` (touched incidentally by
`make core`'s build step, not by this change) and a stale PRE001 -- resolved
by `git checkout -- frob-core/Cargo.lock strata-core/Cargo.lock` and
`frob ticket sweep T-0216` before the final clean delta run above.
`git diff main --diff-filter=D --stat` is empty (playbook section 9, no
unintended deletions).
