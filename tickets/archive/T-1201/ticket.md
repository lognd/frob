---
id: T-1201
title: 'refactor: split verb (built on T-1072/T-1077 family-extraction pattern)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
- T-1199
- T-1200
- T-1267
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- docs/commands/refactor.md
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim
- tests/test_refactor.py::TestRunSplit::test_split_chunk_failure_does_not_touch_later_chunks
- tests/test_refactor.py::TestCli::test_run_refactor_command_dispatches_split_end_to_end
- tests/test_refactor.py::TestCli::test_run_refactor_command_split_refusal_exit_code
designated_repro_test: null
acceptance:
- text: 'GIVEN a source module with N symbols named for a split into a new sibling

    module WHEN `frob refactor split` completes THEN the new module contains

    the moved symbols, the source module re-imports and re-exports every

    moved name unchanged (external `from source import symbol` call sites

    require no edit), and every frob:* directive attached to a moved symbol

    resolves at its new location with no new gate finding'
  evidence:
  - tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim
- text: 'GIVEN a split naming more symbols than fit one safe apply-and-verify

    chunk WHEN the split runs THEN it applies and verifies in multiple

    chunks, each individually refuse-and-rollback safe, rather than failing

    the entire split on one chunk''s problem'
  evidence:
  - tests/test_refactor.py::TestRunSplit::test_split_chunk_failure_does_not_touch_later_chunks
threat: null
component: null
---
<!-- frob:waive DOC006 reason="'frob refactor split' names this ticket's own not-yet-built deliverable (T-1267/T-1135 design), a future CLI verb that structurally cannot resolve against today's subcommand tree until this ticket ships it" -->
Design: docs/design/refactor-verb.md (T-1135). New `frob refactor split`
verb, built directly on the T-1072/T-1077 manual family-extraction
pattern used repeatedly this drive (private sibling module per cohesive
family, old module re-imports/re-exports every moved name UNCHANGED so
external `from frob.x import y` call sites never change, frob:* directives
travel with the moved code, DRIFT002/AFFECT001 doc/test references
updated, land incrementally with full-suite verification per chunk).

Depends on T-1197 (resolve/plan/apply/verify pipeline), T-1199 (directive/
waiver carrier), and T-1200 (registry/evidence repointer) all being
callable, since a split is a move of N symbols at once plus generation of
the re-export shim in the source module.

Scope for this ticket: the split-specific pieces only --
- CLI surface: `frob refactor split SOURCE_MODULE --symbols a,b,c --into
  NEW_MODULE` (exact flag shape TBD during implementation).
- Re-export shim generation in the source module (a well-formed `from
  .new_module import a, b, c  # noqa: F401`-style re-export block,
  matching the exact shape T-1072/T-1077 hand-wrote).
- Chunked apply: a split naming many symbols applies and verifies in
  batches (mirroring T-1072/T-1077's own "land incrementally, verify
  after each chunk" discipline) rather than one all-or-nothing giant
  diff, while still being one refuse-and-rollback transaction per chunk
  (not per whole split) per T-1135's transaction model.
- Re-running T-1197/T-1199/T-1200's move/rewrite machinery per symbol
  moved, not reimplementing rewrite logic here.