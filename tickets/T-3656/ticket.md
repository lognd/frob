---
id: T-3656
title: 'refactor split/move: import-consolidation pass edits string-literal content,
  not just AST import nodes'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the coordinator with production evidence: T-3595's land commit 2b188e958 deleted 'from pathlib import Path' from INSIDE the PY_SAMPLE bytes literal in tests/conftest.py (hunk around line 1558: the literal starts PY_SAMPLE = b"""\ then 'import os' then the deleted pathlib line) -- that line was fixture sample TEXT the outline/import scanner tests parse as a SEPARATE embedded source string, not a real module-level import of tests/conftest.py itself. Removing it broke tests/unit/test_outline.py::test_py_outline_imports on both POSIX legs (run 33521416410).

Root-cause direction: whichever pass in src/frob/refactor decides removable/consolidatable imports (the T-3645 import-consolidation work, or an existing prune/dedupe pass under _scan.py/_transaction.py) is operating on raw text lines rather than genuine top-level ast.Import/ImportFrom nodes for the file being edited -- or it maps AST line numbers computed against one file revision onto a stale/different revision's line offsets. Either way this violates the standing token/grammar-not-lexical rule (memory: token-grammar-fixes-never-lexical): a byte string literal containing import-shaped text must never be treated as a real import statement.

Regression test to add: a source file whose top-level string/bytes literal contains lines that LOOK like 'import X' or 'from X import Y' must survive a split/move with that literal byte-identical -- assert the literal's exact text is unchanged before and after, not just that the file still parses.

Scope note: the FIXTURE restore itself (tests/conftest.py's PY_SAMPLE content) is assigned to a different series/ticket -- do not touch tests/conftest.py from this ticket. This ticket is the refactor-tooling fix only: make the consolidation/prune pass operate on real ast nodes (or correct line-mapping) so it can never again touch bytes inside a string/bytes literal.