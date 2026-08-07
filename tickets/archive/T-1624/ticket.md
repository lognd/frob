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
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_comment_line_is_not_mistaken_for_a_block
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_grammar_parsed_duplicate_blocks_fire_not_lexical_text
designated_repro_test: null
threat: null
component: null
---
Nearly every node in design/frob.strata carries TWO byte-identical `attr interface=[...]` blocks. 45 blocks across ~17 nodes. Measured on node `checker`: block 0 and block 1 both list the same 11 symbols, differing only in a trailing comma.

This predates the 2026-08-05 sync-interface run (verified by inspecting the file at an earlier commit), so it is a long-standing bug, not fresh damage.

Root cause to confirm: `frob sys sync-interface` APPENDS a fresh interface block rather than REPLACING the existing one. The parser evidently tolerates it (last-wins, or first-wins) which is exactly why nobody noticed -- the file stayed semantically correct while doubling in size.

Fix: sync-interface replaces in place. Then a one-time pass removing the duplicate blocks.

Add a lint: more than one `attr interface=` on a single node is an error. A declaration language whose own declarations can silently duplicate cannot be the source of truth for anything -- and this file is supposed to be the source of truth for the whole self-model.

Expected effect: the file loses several hundred lines of pure redundancy, and a whole class of "which block is authoritative?" ambiguity disappears.