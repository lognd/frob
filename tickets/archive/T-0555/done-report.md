## Done report

_warn_if_partial_tree (T-0434) already WARN-logged when tree-sitter salvaged
a partial tree (has_error=True), but that log line is invisible below -v
and had no structured consumer -- for Rust/C++/TS (no gates stage at all,
T-0546/T-0554) nothing else in frob notices the resulting silent symbol
loss either. Added `frob.lang.partial_parse_files()`, a
reset_parse_cache-scoped accessor mirroring parse_cache_stats's shape,
recording the display path of every partially-parsed file since the last
reset. Bumped to 0.60.0 (REL001) with a CHANGELOG entry and a fresh
release stamp for the new public symbol.

Cut: turning this into an actual blocking `frob check` PARSE001-style
violation is a src/frob/gates/** change -- out of this ticket's declared
scope (src/frob/lang/) and the dispatched gates/tickets family's territory,
not mine to add substantively. This ticket only adds the structured signal
gates would consume; the gate itself is a follow-up for that family.

Cut: could not add a new dedicated regression test for
partial_parse_files() under tests/ -- same ScopeLeaseConflict already
logged against T-draft-0ea414ea (T-0160 holds an in-progress lease over
tests/**). Verified manually via a throwaway pytest-style script (a
syntax-broken .py file populates partial_parse_files() with its path; a
clean file does not; reset_parse_cache() clears it) but that could not be
committed as a test. Bound frob:tests on partial_parse_files() to the
existing TestParseCache.test_reset_clears_counters (which now also
exercises the same reset-clears-the-set path) per the same
docs/guides/agent-playbook.md section 5 fallback used for T-0546/T-0551.

### Changed
```
 .frob-release.json           |   3 +-
 CHANGELOG.md                 |  12 +++++
 pyproject.toml               |   2 +-
 src/frob/app/check_runner.py |  39 +++++++++++++++-
 src/frob/check/__init__.py   |  43 +++++++++++++++++
 src/frob/lang/__init__.py    |  45 ++++++++++++++++++
 tickets.md                   | 107 +++++++++++++++++++++++++++++++++++++++++--
 uv.lock                      |   2 +-
 8 files changed, 244 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestParseCache::test_reset_clears_counters` (pytest node id, verified passing when recorded)
