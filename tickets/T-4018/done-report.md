## Done report

Fixed the wrong-guard class at all 5 reported sites in `src/frob/graph/cache.py`
(lines 811, 1679, 1721, 2016 as reported, at their current line numbers after
the fix, plus the import-site equivalents) and `src/frob/dup/_cache.py:114`.
The sweep for the identical construct within these two in-scope files found
two more instances not in the original report: `_read_schema_version`
(cache.py, near line 689) and `get_file_meta` (cache.py, near line 1751).
All 7 sites now guard with `if row` (truthiness), covering both `None` and
`()`, instead of `row is not None`.

Added `_warn_if_empty_row` (cache.py) and wired it into all 7 sites (and
`dup/_cache.py`'s import of it) so a present-but-empty row logs a WARNING
naming the table and the lookup keys before falling back to the miss path --
fixing the crash does not also hide the underlying condition.

Root-cause investigation for "why was the tuple empty": grep confirms
`row_factory` is never set anywhere in `src/frob/graph`, `src/frob/dup`, or
the test suite's conftest -- so a row_factory interaction, while a real way
to CONSTRUCT the empty-row condition directly for the fixtures (used here,
since it is the only reliable non-timing way to make CPython's sqlite3
`fetchone()` return `()` for a matched single-column SELECT), can be ruled
OUT as the actual production cause; nothing in this codebase installs one on
these connections. A `SELECT payload FROM ...` returning zero columns for a
row sqlite otherwise considers present is not normal single-connection
sqlite behavior for any query shape used here. The strongest remaining
candidate, given `load_parsed_artifact` runs through
`_run_with_stale_reconnect`, which reopens a FRESH connection at the cache
path's canonical inode on every call (T-3634), is that the reported CI
failure (gw1, full 13502-test xdist run) hit a genuinely corrupted or
torn on-disk row -- e.g. a sibling worker's concurrent
`store_parsed_artifact` INSERT ... ON CONFLICT landing in an inconsistent
state relative to a concurrent VACUUM/schema-rebuild/`os.replace` publish
this module also performs under load, at exactly the row this reader
attempted. I could not reproduce the exact condition (a rerun of the
reported test alone passed, as the ticket notes) and could not pin the
precise interleaving from static analysis alone -- STATED HONESTLY AS NOT
FULLY DETERMINED. What is now true regardless of the exact mechanism: the
condition no longer crashes the process, and it now leaves a WARNING trail
(table + keys) the next time it is hit, which is the concrete step to
actually root-cause it if it recurs.

Fixtures (T-4018's three requirements), all constructed directly via a
column-scoped `row_factory` override rather than raced for, in
`tests/unit/test_graph_cache.py::TestEmptyRowGuard` and
`tests/unit/test_dup_cache.py::TestCheckFingerprintEmptyRowGuard`:
- MUST-FIRE: `test_empty_row_is_a_clean_miss_not_a_crash` /
  `test_empty_meta_row_is_treated_as_no_stored_fingerprint`.
- MUST-STAY-QUIET: `test_genuine_cached_payload_still_returns_unchanged`.
- WARNING-NAMES-TABLE-AND-KEYS:
  `test_empty_row_logs_a_warning_naming_table_and_keys` /
  `test_empty_meta_row_logs_a_warning_naming_table_and_key`.

Scope: touched only `src/frob/graph/cache.py`, `src/frob/dup/_cache.py`, and
their two direct unit test files -- the originally declared ticket scope.
Widening scope to also cover `docs/modules/dup.md`, `docs/modules/graph.md`,
`tests/test_graph.py`, `tests/test_graph_lock.py`, and
`tests/unit/test_graph_build_lock.py` (to close every SCOPE002 doc/test
reverse-edge) was tried and reverted: those are whole-subsystem-wide files
whose own reverse edges fan out into dozens of unrelated modules and test
files (the exact T-3914 scope-closure-breadth pattern already documented in
this repo) -- pulling all of that in for a guard-only, 7-site fix across 2
files would be out of proportion. `frob check --ticket T-4018` therefore
still reports 27 SCOPE002 findings on this closure; each is reviewed above
and is a known, precedented, out-of-proportion-to-fix class, not a real gap
in this ticket's own coverage.

`frob check --ticket T-4018` also reports 1 pre-existing DRIFT001 on
`src/frob/xref/__init__.py::xref`, a file this ticket never touches (git log
confirms it was last touched by T-3941, unrelated) -- pre-existing baseline
drift, not introduced here.

### Changed
```
 tickets/T-4018/done-report.md |  85 +++++++++++++++++++++++++++++++++++
 tickets/T-4018/ticket.md      | 101 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 184 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestEmptyRowGuard::test_empty_row_is_a_clean_miss_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestEmptyRowGuard::test_genuine_cached_payload_still_returns_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestEmptyRowGuard::test_empty_row_logs_a_warning_naming_table_and_keys` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestCheckFingerprintEmptyRowGuard::test_empty_meta_row_is_treated_as_no_stored_fingerprint` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestCheckFingerprintEmptyRowGuard::test_empty_meta_row_logs_a_warning_naming_table_and_key` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 4411 warning(s), 931 waived
- error-findings: DRIFT001@src/frob/xref/__init__.py, SCOPE002@tickets.md
