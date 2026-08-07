## Done report

frob sys sync-interface's span-finder (_find_interface_span, now
_find_interface_spans) used to stop scanning a node's body at the FIRST
attr interface=[...] block it found and return that one span alone.
_rewrite_node_interface_block then only ever replaced that first span --
any SECOND interface block elsewhere in the same node body (this repo's
own design/frob.strata has one right after the header AND another right
before the closing brace, non-contiguous, separated by may/code/clearance
attrs) was silently left in place forever. That produced exactly the
observed damage: 45 byte-identical duplicate blocks across ~17 nodes,
predating any single sync run (confirmed by inspecting an earlier commit).

Fix: _find_interface_spans now scans the WHOLE node body and returns
EVERY span found (compact [...] blocks and legacy one-line-per-symbol
lines, freely mixed). _rewrite_node_interface_block merges every span's
declared names, and rewrites whenever more than one span is found (not
just on a symbol-set mismatch) -- collapsing them into exactly one
compact block at the first span's position, deleting the rest.

Applied the fix to design/frob.strata itself via `frob sys
sync-interface` (no --check): 3191 -> 2363 lines, 34 -> 18 interface
blocks (0 duplicates, one per node with a declared surface). Re-ran
--check immediately after: 0 drift (idempotent). Confirmed the file
still parses via frob.lang.parse_file.

Added SYS108 (_duplicate_interface_violations, src/frob/strata/
_selfconform.py): a node whose interface= attrs (read from the real
ELABORATED grammar model, Node.attrs -- not a text scan) name the same
symbol more than once is now a hard ERROR, always (no advisory tier),
wired into _collect_sys_violations and re-exported from
frob.strata.__init__ alongside every other SYS10x id. Ran `frob check
--only sys --ticket T-1624`: 0 errors -- the repo's own now-deduped
design/frob.strata does not trip its own new lint.

Per a mid-task nudge, added two regression tests proving both the
SYS108 check and the sync-interface span-finder are GRAMMAR-aware, not
merely lexical: a '//' comment line containing literal
"attr interface=[public_fn];" text is provably never counted as a
declaration or a span (this language has no block-comment form, only
'//'-prefixed line comments per strata-core/src/parse/lexer.rs), while
the two REAL (non-commented) duplicate blocks on the same node still
fire exactly once.

`frob check --land-parity` could not complete inside its own 400s
foreground budget under the current session's load (multiple concurrent
agents/lands) -- reported here as an unmeasured result, not a clean
result, per the playbook's own instruction not to claim more than was
observed. Scoped `frob check --only test/sys/scope/prework --ticket
T-1624` all read 0 errors.

### Changed
```
 design/frob.strata                       | 1560 +++++++-----------------------
 src/frob/strata/__init__.py              |    2 +
 src/frob/strata/_selfconform.py          |   60 ++
 src/frob/strata/_sync_interface.py       |  161 +--
 tests/unit/strata/test_selfconform.py    |  112 +++
 tests/unit/strata/test_sync_interface.py |   81 ++
 tickets.md                               |   81 +-
 7 files changed, 790 insertions(+), 1267 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_comment_line_is_not_mistaken_for_a_block` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_grammar_parsed_duplicate_blocks_fire_not_lexical_text` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 258 warning(s), 865 waived
- error-findings: none (measured, zero errors)
