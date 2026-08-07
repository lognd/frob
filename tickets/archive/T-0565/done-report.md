## Done report

Root-caused two structural gaps in the substrate, rather than mass-waiving:

1. `build_reference_graph` (src/frob/graph/callgraph.py) only ever scanned
   `body_tokens`. A module-level dispatch dict (`_DISPATCH_BY_TYPE = {"cpp":
   _dispatch_check_cpp, ...}`) has NO body at all -- `RawSymbol.body_tokens`
   is always `()` for CONST/TYPE kinds -- so its referenced private helpers
   were invisible no matter how broad the token scan got. Root cause turned
   out to be one level deeper still: `_walk_python._const_assignment_name`
   rejected any name starting with `_` (`name[0].isalpha()`), so a PRIVATE
   dispatch-table constant was never even turned into a `RawSymbol` --
   invisible to the whole symbol list, not merely under-recalled. Fixed
   both: `_referenced_names` now scans `sig_tokens` (where a const's whole
   assignment, including RHS, and a function's parameter list both live) in
   addition to `body_tokens`; `_const_assignment_name` accepts a leading
   underscore. `build_call_graph`'s `_called_names` extractor is untouched
   (kept body-only via a new `_called_names_from_sym` wrapper) since
   `frob.dup`'s helper-inline triage reasons about "called", not "mentioned
   anywhere", and widening its recall would be an unasked-for behavior
   change.

2. Triaged the residual by hand (grep-verified each): roughly a dozen
   "false positives" turned out to be a THIRD bug, not a recall gap --
   `frob:tests`/directives placed above the TEST function instead of above
   the SOURCE symbol (backwards from the documented DSL convention: `Edge.
   src` binds to whatever the comment sits directly above). Moved/added the
   directive onto the source symbol in each case: `_scan_file_operations`
   (vet/_capability.py), `_unexcused_empty_cells`/`_validate_registry_kinds`
   (vet/_capability_registry.py), `HostOwns._validate_mode`/`HostManifest.
   _validate_listens` (strata/_host.py), `_close_all` (dup/_cache.py,
   removed the backwards duplicate in tests/unit/test_dup_cache.py), and
   added a fresh one for `PolicyDecl._split_meta_rules` (strata/_ast.py,
   a pydantic before-validator exercised by an existing parse test that had
   no directive at all).

Genuinely dead, deleted after a `grep -rn` proving zero references outside
their own definition: `_reaches` (gates/_refs.py, its own docstring's "the
single-text convenience call site" never existed), `_edge_symref_path`
(testing/_select.py), `_is_shadowed` (vet/_capability.py -- its sibling
`_rust_is_shadowed`/`_c_is_shadowed` ARE called, but the python one's real
call sites all use `_shadowing_scope` directly), `_find_dir_path` (tickets/
_store.py, plus its now-orphaned `_TICKET_FILENAME_RE` regex constant),
`_facet_for_ref` (graph/lock.py -- explicitly superseded by `_facets_for_ref`
per its own docstring, "kept for external callers" that grep shows do not
exist).

Waived (not deleted, not fixable structurally): two pytest `autouse=True`
fixtures (`tests/test_dup_cross_lang.py::_isolated_dup_cache`, `tests/unit/
test_dup_cache.py::_close_cached_connections`) -- invoked by the test
runner for every test in their module with NO referencing token anywhere,
the one false-positive class the sig_tokens+body_tokens broadening cannot
see by construction (there is no site to see). Each waiver reason states
this explicitly.

Result: DEAD001 findings went from 51 to 4 -- 2 waived (above), 2 residual
in src/frob/gates/__init__.py (`_documented_srcs`, `_run_jobs`) left
UNTOUCHED because a sibling agent owns that file this wave; not filed as
T-draft-9305d3de (never refiled) with the same "check directive placement first" guidance
this ticket's own triage discovered, so that follow-up does not re-derive
it from scratch.

`frob check --ticket T-0565` is clean on every gate this ticket's scope
touches (COV, DEAD). The two `gate:LANG` errors visible in an unscoped run
are pre-existing, from a same-day sibling ticket that landed via `git merge
main` (T-0405/T-0406's new lang-conformance gate references a stale
`T-draft-78a0f919` id that doesn't exist in this queue) -- confirmed
unrelated by grep (the reference lives in `src/frob/lang/_support.py`,
which this ticket's scope never touches) and pre-existing on `main` before
this ticket's merge.

### Changed
```
 src/frob/app/check_runner.py          | 21 +++++---
 src/frob/app/clean_runner.py          |  3 +-
 src/frob/app/debt_runner.py           | 25 +++++++---
 src/frob/app/doctor_runner.py         | 11 +++--
 src/frob/app/gitlog_runner.py         | 17 ++++++-
 src/frob/app/registry_runner.py       |  5 +-
 src/frob/app/test_runner.py           | 23 ++++++---
 src/frob/dup/_cache.py                |  2 +
 src/frob/gates/_refs.py               | 12 +----
 src/frob/gates/_render_lint.py        | 23 ++++-----
 src/frob/graph/callgraph.py           | 57 +++++++++++++++++-----
 src/frob/graph/lock.py                | 10 ----
 src/frob/lang/_walk_python.py         | 20 +++++++-
 src/frob/strata/_ast.py               |  2 +
 src/frob/strata/_host.py              |  4 ++
 src/frob/testing/_select.py           |  5 --
 src/frob/tickets/_store.py            | 10 ----
 src/frob/vet/_capability.py           | 10 +---
 src/frob/vet/_capability_registry.py  |  4 ++
 tests/test_debt_runner.py             | 15 ++++--
 tests/test_dup_cross_lang.py          |  1 +
 tests/test_lang.py                    | 23 +++++++++
 tests/unit/test_app_runners.py        | 17 +++++--
 tests/unit/test_app_runners_batch6.py | 12 +++--
 tests/unit/test_dup_cache.py          | 11 ++++-
 tickets.md                            | 92 +++++++++++++++++++++++++++++++++--
 26 files changed, 316 insertions(+), 119 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_private_module_level_const_extracted` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestConnectionReuse::test_close_all_drops_cached_connections` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_names_registry_entry` (pytest node id, verified passing when recorded)
