---
id: T-0893
title: lang/** tree-sitter parse has no file-size cap or timeout -- untrusted-file
  DoS trust-boundary gap
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/__init__.py
- tests/test_lang.py
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_lang.py
  reason: T-0893's fix needs regression tests + a doc section for the new size-cap/timeout
    guard, both outside the original src-only scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/lang.md
  reason: T-0893's fix needs regression tests + a doc section for the new size-cap/timeout
    guard, both outside the original src-only scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_lang.py::TestSizeCapAndTimeout::test_oversized_file_is_skipped_loudly
- tests/test_lang.py::TestSizeCapAndTimeout::test_parse_timeout_returns_err_not_hang
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep).

frob.lang's tree-sitter ingestion (`_parse` in src/frob/lang/__init__.py,
~line 316-370) reads the ENTIRE file into memory (`path.read_bytes()`) and
hands it to tree-sitter's `parser.parse(source)` with no file-size cap and
no parse timeout, for every file frob's graph walk visits -- including
files under an audited/untrusted repo tree (this is a general-purpose
static-analysis tool other people's repos get pointed at, not just this
one's own source). Tree-sitter's incremental-parse error recovery is
generally robust but is not immune to pathological-input classes (deeply
nested brackets/parens driving quadratic-ish recovery, or simply a
multi-GB single file) -- and there is no structural guard here at all, not
even a generous one: no `st_size` check before `read_bytes()`, no
wall-clock budget around `parser.parse()`.

Fix direction: add a configurable max-file-size guard (skip + record a
PARSE001-shaped "too large to parse" finding rather than attempt it) and a
wall-clock timeout around the tree-sitter parse call in `_parse`, so a
single adversarial or merely enormous file cannot hang or exhaust memory
in a `frob check` run over an untrusted tree.