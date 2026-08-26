---
id: T-1602
title: 'Language support: CUDA'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1597
tier: ticket
sprint: post-1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/**
- src/frob/lang/_walk_cuda.py
- src/frob/lang/_walk_c.py
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
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/**
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/lang/_walk_cuda.py
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/lang/_walk_c.py
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/fixtures/lang/**
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang.py
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_support.py
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/lang.md
  reason: 'T-2446: same convention as the other per-language leaves, PLUS the existing
    C walker (src/frob/lang/_walk_c.py) since the ticket''s own body says ''decide
    explicitly whether CUDA is a distinct adapter or a C++ dialect flag'' -- either
    resolution touches one of these two named files, not a guess'
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add CUDA to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: A C++ superset, so the C++ adapter is the starting point, but kernel qualifiers (__global__, __device__, __host__) are the whole point: they are the visibility and execution-surface concepts that matter, and a kernel entry point is the analog of a public symbol. Files are .cu/.cuh. Decide explicitly whether CUDA is a distinct adapter or a C++ dialect flag -- and record why.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.