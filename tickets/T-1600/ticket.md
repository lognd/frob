---
id: T-1600
title: 'Language support: C#'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: post-1.0
runs_last: false
scope:
- src/frob/lang/_walk_csharp.py
- tests/fixtures/lang/**
- tests/test_lang.py
- tests/test_lang_conformance_gate.py
- tests/test_lang_support.py
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/**
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/lang/_walk_csharp.py
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/fixtures/lang/**
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang.py
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_support.py
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/lang.md
  reason: 'T-2446: narrowed to the existing per-language walker naming convention
    (src/frob/lang/_walk_<lang>.py, confirmed via ls src/frob/lang/), the shared fixture
    dir (tests/fixtures/lang/sample.<ext>, one file per language, confirmed via ls),
    the three existing lang/conformance-gate/support test suites, and the repo''s
    single lang doc (docs/modules/lang.md, confirmed via ls docs/modules/) -- not
    a guess, matches this repo''s own established convention for every other adapter'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/lang/**
  reason: 'T-2446 follow-up: forgot this removal in the same pass -- narrowed to the
    specific walker file already, the umbrella glob was a leftover'
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add C# to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: Roslyn-shaped visibility (public/internal/protected/private), partial classes, properties vs fields, namespaces, and attributes. Nullable reference type annotations must not confuse symbol extraction. XML doc comments (triple-slash) are the doc-comment form.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.