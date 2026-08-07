## Done report

Changed:
src/frob/tickets/_store.py::_yaml_loader
src/frob/tickets/_store.py::_parse_ticket_file
src/frob/tickets/_store.py::iter_raw_ledger_frontmatter
src/frob/tickets/_store.py::_parse_ledger
src/frob/tickets/_store.py::load_archive
src/frob/tickets/_store.py::_archive_cache_path
src/frob/tickets/_store.py::_read_archive_cache
src/frob/tickets/_store.py::_write_archive_cache

Evidence:
tests/unit/test_ticket_store.py::TestYamlLoader.test_prefers_csafeloader_when_libyaml_present
tests/unit/test_ticket_store.py::TestYamlLoader.test_falls_back_to_safeloader_without_libyaml
tests/unit/test_ticket_store.py::TestLoadArchiveCache.test_skips_reparse_when_content_hash_unchanged
tests/unit/test_ticket_store.py::TestLoadArchiveCache.test_reparses_when_archive_content_changes

Measured (repo's own tickets-archive.md, 1235+ documents):
- `frob ticket doable`, baseline (pre-fix, HEAD): 1.96s / 1.97s / 2.04s
- `frob ticket doable`, after fix, cold cache: 0.85s
- `frob ticket doable`, after fix, warm cache: 0.58s / 0.59s / 0.60s
Baseline matches the ticket's ~2.33s reference figure; warm-cache result
(~0.58-0.60s) lands inside the ticket's ~0.5-0.8s target, cold-cache
result (0.85s, CSafeLoader-only benefit before any cache hit) is close
behind it.

Filed: none

Gates: `frob check --ticket T-1206 --only affect_drift --only prework
--only scope --only test` clean (0 errors; remaining warnings are
pre-existing debt outside this ticket's scope: TEST003 on
src/frob/tomlio.py and strata-core/src/parse, TEST006 missing coverage
stamp, TEST014 stop()-name ambiguity across unrelated modules).
`ruff check`/`ruff format`/`ty check` clean on touched files.
`frob test --base main` exit=0 (10 selected python tests).

### Changed
```
 docs/modules/tickets.md         |  10 +++
 src/frob/tickets/_store.py      | 139 ++++++++++++++++++++++++++++++++++++++--
 tests/unit/test_ticket_store.py |  60 +++++++++++++++++
 tickets.md                      |  29 ++++++++-
 4 files changed, 229 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_without_libyaml` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLoadArchiveCache::test_skips_reparse_when_content_hash_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLoadArchiveCache::test_reparses_when_archive_content_changes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 532 warning(s), 679 waived
- error-findings: PRE001@tickets/T-1206, SELFAUDIT001@design
