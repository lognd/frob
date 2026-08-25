---
id: T-1604
title: 'Language support: Bash/Shell'
state: in-progress
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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_bash.py
- tests/fixtures/lang/**
- tests/test_lang.py
- tests/test_lang_conformance_gate.py
- tests/test_lang_support.py
- docs/modules/lang.md
- src/frob/lang/_extract.py
- src/frob/lang/__init__.py
- src/frob/gates/_lang_conformance.py
- src/frob/lang/_support.py
- frob.toml
- tickets/T-draft-f424b6c4/**
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
  glob: src/frob/lang/_walk_bash.py
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
- op: add
  glob: src/frob/lang/_extract.py
  reason: wiring the new bash walker into central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE)
    requires editing these two files, same as T-0723 did for kotlin; declared scope
    narrowly (two files, not src/frob/lang/**) to minimize lock footprint
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/lang/__init__.py
  reason: wiring the new bash walker into central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE)
    requires editing these two files, same as T-0723 did for kotlin; declared scope
    narrowly (two files, not src/frob/lang/**) to minimize lock footprint
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_lang_conformance.py
  reason: the behavioral conformance suite (T-2365) requires a per-language fixture
    source registered in this file (_CAPABILITY_FIXTURE_SOURCES/_CAPABILITY_FIXTURE_EXTENSIONS)
    or test_implemented_capability_behaves_as_claimed fails once bash is registered
    in _EXTENSION_TABLE and its symbol_walk/publicness/doc_extract/directive_parse/call_graph/import_graph
    capabilities go IMPLEMENTED; narrow single-file addition, not touching any gate
    logic other agents in gates/ are working on
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/lang/_support.py
  reason: bash's call syntax (bare-word invocation, no parenthesized args) cannot
    be recognized by frob.graph.callgraph's shared token-based call detector (identifier-immediately-followed-by-'('
    heuristic, T-0565) -- must declare CAPABILITY_CALL_GRAPH as a reasoned KNOWN_GAP
    for bash rather than a false IMPLEMENTED claim; a one-branch addition to an existing
    per-language dispatch function, not new machinery
  actor: logan
  at: '2026-08-25'
- op: add
  glob: frob.toml
  reason: frob test selection now treats tests/fixtures/lang/sample.sh (a bash SOURCE
    fixture, not runnable test code -- same T-0149 shape as the existing .strata litmus-fixture
    entry) as a bash test-selection candidate once bash is a supported frob.lang extension,
    and fails NoRunner without a [[test.runner]] entry naming the real covering pytest
    suite; mirrors the existing strata [[test.runner]] entry exactly
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tickets/T-draft-f424b6c4/**
  reason: the finding filed against the shared call-graph layer (frob.graph.callgraph
    bash bare-word invocation gap) is a new tracked file in this branch's diff; SCOPE001
    flags it as outside T-1604's declared scope even though tickets/** is normally
    exempt from the root-write-guard -- narrow grant covering just this one draft's
    own directory
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add Bash/Shell to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: The hardest of the five for the abstraction, and therefore the most valuable probe. There is no visibility concept, functions can be redefined, sourcing is dynamic, and much meaningful code is top-level statements rather than named symbols. Decide and document what a public symbol IS here (exported functions? every function? script entry points?) before implementing. Hash-only line comments, no block comments, so directive continuations matter.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.