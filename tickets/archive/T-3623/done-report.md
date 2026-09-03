## Done report

Fixed T-3607 fallout: a cache-recreate schema-visibility race that
could raise sqlite3.OperationalError: no such table: meta straight out
of _check_fingerprint (cache.py:377). T-3607's quarantine-rename
_recreate opened a fresh, EMPTY sqlite file directly at the real cache
path and applied its schema in a later step -- a concurrent connection
racing that window could see a valid-but-tableless file.

Fix: build the replacement's full schema at a throwaway temp path
first (before quarantining the old file, so the real path stays
continuously present -- building before quarantining also avoids
regressing T-3607's own concurrent-reader test, which needs the real
path to never be transiently missing), then publish it into place with
one atomic os.replace. Same schema-complete-before-visible treatment
for the very first ever connect() at a brand-new path. Added a bounded
recovery retry around _check_fingerprint itself as direction 2's
defense-in-depth, so any residual no-such-table-meta race can never
escape connect() uncaught.

Evidence: tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb
(3 new tests, including a genuine two-process regression test that
reproduced the original race before the _check_fingerprint recovery
layer was added, and stayed green after). Full
tests/unit/test_graph_cache.py (10/10), tests/test_graph.py plus
tests/test_graph_lock.py (175/175 combined), and
tests/test_coverage_wait_shared.py (10/10, the originally-reported
failing test's file) all pass, 3x repeated on the cache test file with
no flakes.

Filed: none.

### Changed
```
 src/frob/graph/cache.py        | 121 ++++++++++++++++++++++++++++++++++++-
 tests/unit/test_graph_cache.py | 134 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-3623/ticket.md       |   4 ++
 3 files changed, 258 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_recreate_replacement_always_has_meta_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_first_ever_connect_never_exposes_a_tableless_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 15 error(s), 4144 warning(s), 902 waived
- error-findings: ARCH001@src/frob/graph/cache.py, ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LANDPARITY002@src/frob/graph/cache.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3623, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
