## Done report

Implemented the three free-text carriers `_directives.py`/`_repointer.py` do
not reach: `scan_python_prose_mentions` (docstring/comment prose anywhere
in the repo naming the moving symbol's old dotted path or symref, skipping
`frob:*` directive-owning spans to avoid a double rewrite with T-1199's
carrier), `scan_docs_prose_mentions` (docs/** prose sentences and fenced
code blocks citing the old import path), and `scan_doc_anchor_carriers`
(a doc heading embedding the moved symbol/module name gets its text and
`frob.graph.dsl.slugify` anchor slug rewritten together, then every
`frob:doc`/markdown reference to the old anchor repointed). All three are
word-boundary matched (no partial-word false positive inside an unrelated
longer name) and wired into `build_plan` via a new `_prose_carrier_ops`
helper alongside the T-1199/T-1200 carriers already there. An unreadable
file is disclosed in `unresolved` as "review by hand", never silently
skipped (epic acceptance [3]).

In passing (per dispatch note): fixed the 8 SELFAUDIT SYS104 gaps T-1199
left (6 refactor symbols + 2 testsuite classes) via `frob sys
sync-interface` (now covers node attr blocks), and split the 73-line
`scan_directive_carriers` (ARCH001) into a thin repo-wide loop plus a new
private `_scan_file_for_directive_carriers` per-file helper.

### Changed
```
 design/frob.strata                |   8 ++
 docs/commands/refactor.md         |  57 ++++++++-
 src/frob/refactor/__init__.py     |  16 +++
 src/frob/refactor/_directives.py  | 237 +++++++++++++++++++++++++++++++++++
 src/frob/refactor/_repointer.py   | 256 ++++++++++++++++++++++++++++++++++++++
 src/frob/refactor/_transaction.py |  51 +++++++-
 tests/test_refactor.py            | 211 +++++++++++++++++++++++++++++++
 tickets.md                        | 187 +++++++++++++++++++++++++---
 8 files changed, 1006 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestProseCarrier::test_docstring_mention_elsewhere_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestProseCarrier::test_directive_line_skipped_by_prose_scan` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestProseCarrier::test_docs_prose_and_code_block_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestProseCarrier::test_heading_and_anchor_rewritten_together` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestProseCarrier::test_unrelated_heading_not_touched` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestProseCarrier::test_unreadable_doc_file_disclosed_in_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 269 warning(s), 746 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w16d-refactor/src/frob/refactor/_directives.py:59
