---
id: T-1624
title: 'strata: sync-interface appends duplicate attr interface blocks instead of
  replacing'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/strata/_sync_interface.py
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_sync_interface.py
- tests/unit/strata/test_selfconform.py
- src/frob/strata/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/__init__.py
  reason: SYS_DUPLICATE_INTERFACE constant needs the same public re-export __init__.py
    already does for every other SYS10x rule id
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/strata/**
  reason: narrow to files actually touched; the two broad globs from ticket filing
    are superseded by explicit adds
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/**
  reason: narrow to files actually touched; the two broad globs from ticket filing
    are superseded by explicit adds
  actor: logan
  at: '2026-08-06'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_grammar_parsed_duplicate_blocks_fire_not_lexical_text
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_comment_line_is_not_mistaken_for_a_block
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
threat: null
component: null
anchor: false
anchor_reason: null
---
Nearly every node in design/frob.strata carries TWO byte-identical `attr interface=[...]` blocks. 45 blocks across ~17 nodes. Measured on node `checker`: block 0 and block 1 both list the same 11 symbols, differing only in a trailing comma.

This predates the 2026-08-05 sync-interface run (verified by inspecting the file at an earlier commit), so it is a long-standing bug, not fresh damage.

Root cause to confirm: `frob sys sync-interface` APPENDS a fresh interface block rather than REPLACING the existing one. The parser evidently tolerates it (last-wins, or first-wins) which is exactly why nobody noticed -- the file stayed semantically correct while doubling in size.

Fix: sync-interface replaces in place. Then a one-time pass removing the duplicate blocks.

Add a lint: more than one `attr interface=` on a single node is an error. A declaration language whose own declarations can silently duplicate cannot be the source of truth for anything -- and this file is supposed to be the source of truth for the whole self-model.

Expected effect: the file loses several hundred lines of pure redundancy, and a whole class of "which block is authoritative?" ambiguity disappears.

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
