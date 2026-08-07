## Done report

G6 (full fix, T-0402 residual): `src/frob/graph/cache.py`'s
`_FINGERPRINT_PACKAGES` hand-copied the tree-sitter grammar packages
`frob.lang` depends on -- a new/changed grammar package silently served a
stale cache under an unchanged fingerprint (the exact T-0243 incident this
mechanism exists to prevent). Added `frob.lang.GRAMMAR_FINGERPRINT_PACKAGES`
(new public constant: `{"tree-sitter", "tree-sitter-language-pack"}` --
every non-`.strata` grammar in `_EXTENSION_TABLE` loads through
`tree_sitter_language_pack.get_parser`, so this pair is the entire
fingerprint surface for all six grammars today). `_FINGERPRINT_PACKAGES` is
now `(*_NON_LANGUAGE_FINGERPRINT_PACKAGES, *sorted(GRAMMAR_FINGERPRINT_PACKAGES))`
-- derived, single source of truth, instead of a second hand-maintained
tuple. `frob`/`strata-core` stay explicit in cache.py since they are not
`frob.lang` grammar packages.

G7 (T-0402 residual): `_parse_source_file_fresh` used to store the
`on_disk_hash` its CALLER (`_process_source_file`) had read separately,
before ever calling `parse_file`/`_parse_strata_file` (which does its own,
second, read). A write landing between the two reads stored the SECOND
read's symbols under the FIRST read's hash -- a cached row whose hash no
longer described its own symbols. `ParsedFile.content_hash` was already
computed by `frob.lang` from the exact bytes it read and parsed (both the
tree-sitter and strata branches build it via the shared
`_build_parsed_file` tail) -- `_parse_source_file_fresh` now stores
`parsed.content_hash` instead of the caller's earlier hash, closing the
window: there is exactly one read whose bytes the stored hash describes.
The early `_content_hash` read in `_process_source_file` still exists and
is still needed (deciding WHETHER a reparse is needed at all, the T-0245
stat-first fast path), it is just never trusted for what gets STORED
anymore.

Tests (tests/test_graph.py, TestBuildIncremental):
- test_fingerprint_packages_derived_from_lang_registry: asserts
  `GRAMMAR_FINGERPRINT_PACKAGES <= set(_FINGERPRINT_PACKAGES)` and that
  `frob`/`strata-core` are still present.
- test_stored_hash_matches_bytes_actually_parsed: monkeypatches
  `frob.graph._content_hash` to return a deliberately wrong value (the old
  code path this simulates would have stored that wrong value), builds the
  graph, and asserts the `files` table's stored `content_hash` equals the
  REAL hash of the file's bytes, not the deliberately-wrong decision hash
  -- proves the fix, not just "a build succeeds".

Merge note: `main` moved to `ca28fe1` (T-0412/T-0456/T-0507 debt+journal
chain, tip at 0.55.0) while this ticket was in flight in this same
worktree. Merged main in (a mid-ticket code merge, not a late ledger sync,
per the playbook's guidance) and hit a real `CHANGELOG.md` collision: both
sides had independently claimed overlapping version numbers (this
worktree's T-0358/T-0433 work at 0.54.0/0.55.0 vs main's T-0412/T-0456
work also at 0.55.0/0.54.0). Resolved by combining T-0358+T-0433 under one
fresh `0.56.0` header above main's already-landed entries and re-running
`frob release stamp` against the fully merged tree -- `pyproject.toml` is
now 0.56.0, `.frob-release.json` stamped at 0.56.0.

REL001: `GRAMMAR_FINGERPRINT_PACKAGES` is a new public symbol; covered by
the 0.56.0 bump above (shared with T-0358's stale_install_warning bump,
since both were in flight in the same worktree session before either was
tagged as a real release).

Scope: added `docs/modules/lang.md` (frob:doc anchor for the new public
constant), `tests/test_graph.py` (new regression tests), `CHANGELOG.md` /
`pyproject.toml` / `.frob-release.json` / `uv.lock` (REL001), and
`src/frob/tickets/__init__.py` / `src/frob/tickets/_models.py` /
`tests/test_tickets_scope_mutation.py` -- same SCOPE001 cross-ticket-
exemption gap already disclosed in T-0358's Done report (T-0485's commit
subject omitted its own ticket id, so `_commit_exempts_file`'s subject-line
match can't attribute those already-landed hunks away from every
subsequent ticket's diff on this shared worktree branch).

### Changed
```
 .frob-release.json                   |   4 +-
 CHANGELOG.md                         |  20 +++
 docs/modules/lang.md                 |  13 ++
 pyproject.toml                       |   2 +-
 src/frob/__main__.py                 |   8 +-
 src/frob/app/config.py               |  67 ++++++++
 src/frob/graph/__init__.py           |  28 +++-
 src/frob/graph/cache.py              |  28 ++--
 src/frob/lang/__init__.py            |  20 +++
 src/frob/tickets/__init__.py         |  21 ++-
 src/frob/tickets/_models.py          |  17 ++
 tests/test_graph.py                  |  48 ++++++
 tests/test_tickets_scope_mutation.py |  58 ++++++-
 tests/unit/test_config.py            |  76 +++++++++
 tickets.md                           | 297 ++++++++++++++++++++++++++++++++++-
 uv.lock                              |   2 +-
 16 files changed, 676 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildIncremental::test_stored_hash_matches_bytes_actually_parsed` (pytest node id, verified passing when recorded)
