## Done report

Fixed _scope_globs (frob.tickets._models) so a bare directory scope entry
with NO trailing slash (e.g. "docs/modules") is expanded to also match the
subtree (entry + "/**"), same as the trailing-slash case, instead of being
treated as a dead literal fnmatch pattern that can never match a real
file path. An entry whose final path segment carries a dot-extension
(a literal file reference like "src/frob/foo.py") is left untouched.
Added a regression test covering the recursive match, the sibling-dir
non-match, and the literal-file-is-not-a-directory case.

### Changed
```
 src/frob/tickets/_models.py | 25 ++++++++++++++++++++++---
 tests/test_tickets.py       |  9 +++++++++
 tickets.md                  | 29 ++++++++++++++++++++++++++---
 3 files changed, 57 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeMatching::test_bare_dir_entry_no_trailing_slash_globs_recursively` (pytest node id, verified passing when recorded)
