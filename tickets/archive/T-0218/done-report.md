## Done report

**Did NOT reproduce on current main.** Investigated both build-summary log
sites that could plausibly print `edges=0` on a cache-hit build:

- `src/frob/graph/__init__.py::_finalize_build` (the `build_graph: done,
  parsed=%d hits=%d symbols=%d edges=%d malformed=%d` line the ticket
  quotes) -- `edges=%d` is `len(snapshot.edges)`, and `snapshot` comes from
  `_cache.load_all(conn, stats=stats)` (`src/frob/graph/cache.py::load_all`),
  which reassembles `edges` by querying the `edges` table for every file row
  currently in the db -- fresh-parsed AND cache-hit files alike (`load_all`
  loop calls `load_file_data(conn, path)` for every `path in file_hashes`,
  not just newly-parsed ones). `BuildStats` (`src/frob/graph/_models.py`)
  has only `parsed`/`cache_hits` fields -- no `edges` field exists anywhere
  to be misread as 0.
- `src/frob/app/graph_runner.py::_run_build` (the `frob graph build` CLI's
  own summary line) -- same pattern, `edges=%d` is `len(snapshot.edges)`
  from the same `build_graph()` return value.

`git log -p` on both files confirms `len(snapshot.edges)` has been used
since the log line was first introduced (commit `d918bb8`) -- there was
never a fresh-parse-only counter plumbed into either format string to
regress from.

**Reproduction attempt** (`uv run python`, root=this repo, ~472 files):
cold build then a second all-cache-hit build against the same
`cache.db`, both read back via the real `build_graph()`:
```
BUILD1 parsed=472 cache_hits=0   edges=3763
BUILD2 parsed=0   cache_hits=472 edges=3763
```
Second (cache-hit) run reports the true edge count, not 0.

Added a regression litmus (`tests/test_graph.py::TestBuildIncremental::
test_cache_hit_build_reports_real_edge_count`) asserting a second,
all-cache-hit `build_graph()` call reports `len(snapshot.edges) ==` the
first build's edge count and `> 0` -- pins this behavior so a future
change that plumbs a fresh-parse-only edge counter into the log line
would fail this test.

Changed: tests/test_graph.py::TestBuildIncremental.test_cache_hit_build_reports_real_edge_count (new test only; no src/frob/graph/** change -- nothing to fix)
Evidence: tests/test_graph.py::TestBuildIncremental::test_cache_hit_build_reports_real_edge_count (collected via `pytest tests/test_graph.py -o addopts="" --collect-only -q`)
Filed: none
Gates: `uv run frob check --delta --ticket T-0218` after `--stamp-baseline` and a fresh `frob ticket sweep T-0218` -> `0/1 new  0 errors, 0 warnings, 24 waived` (the 1 kept violation is the repo's pre-existing waived-elsewhere baseline entry, unrelated to this change). `ruff check`, `ruff format --check`, `ty check` on tests/test_graph.py and src/frob/graph/ all clean. `pytest tests/test_graph.py tests/test_graph_lock.py` green (all passing). Merged `main` (tip `a0c54a5`, "fix(strata): SYS102 missing-package-root is DEBUG not WARNING in non-frob repos (T-0211)") into the worktree; `git diff main --diff-filter=D --stat` is empty.

Not closing per dispatch instructions -- leaving for reviewer.
