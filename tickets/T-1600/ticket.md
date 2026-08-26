---
id: T-1600
title: 'Language support: C#'
state: done
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
- src/frob/lang/_walk_csharp.py
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
- tickets/T-2905/**
- tickets/T-2906/**
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
- op: add
  glob: src/frob/lang/_extract.py
  reason: 'same wiring surface T-1604 needed for bash: central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE),
    behavioral-conformance fixture registration, and (if the same test-selection issue
    reproduces for a tests/fixtures/lang/*.cs SOURCE fixture) a [[test.runner]] entry'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/lang/__init__.py
  reason: 'same wiring surface T-1604 needed for bash: central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE),
    behavioral-conformance fixture registration, and (if the same test-selection issue
    reproduces for a tests/fixtures/lang/*.cs SOURCE fixture) a [[test.runner]] entry'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_lang_conformance.py
  reason: 'same wiring surface T-1604 needed for bash: central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE),
    behavioral-conformance fixture registration, and (if the same test-selection issue
    reproduces for a tests/fixtures/lang/*.cs SOURCE fixture) a [[test.runner]] entry'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/lang/_support.py
  reason: 'same wiring surface T-1604 needed for bash: central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE),
    behavioral-conformance fixture registration, and (if the same test-selection issue
    reproduces for a tests/fixtures/lang/*.cs SOURCE fixture) a [[test.runner]] entry'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: frob.toml
  reason: 'same wiring surface T-1604 needed for bash: central dispatch (_WALKERS/COMMENT_TYPES/_EXTENSION_TABLE),
    behavioral-conformance fixture registration, and (if the same test-selection issue
    reproduces for a tests/fixtures/lang/*.cs SOURCE fixture) a [[test.runner]] entry'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tickets/T-2905/**
  reason: two findings filed as part of this ticket's own work (wire-or-drop _parse_csharp
    follow-up, and the shared bash+csharp FACETS-wiring finding) are new tracked files
    in this branch's diff; SCOPE001 flags them the same way T-1604's own draft citation
    did
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tickets/T-2906/**
  reason: two findings filed as part of this ticket's own work (wire-or-drop _parse_csharp
    follow-up, and the shared bash+csharp FACETS-wiring finding) are new tracked files
    in this branch's diff; SCOPE001 flags them the same way T-1604's own draft citation
    did
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_lang.py::TestCSharp::test_parse_csharp_produces_a_tree
- tests/test_lang.py::TestCSharp::test_walks_class_and_method
- tests/test_lang.py::TestCSharp::test_private_method_is_not_public
- tests/test_lang.py::TestCSharp::test_property_is_a_const_symbol
- tests/test_lang.py::TestCSharp::test_const_field_is_extracted_plain_field_is_not
- tests/test_lang.py::TestCSharp::test_enum_is_a_type_symbol
- tests/test_lang.py::TestCSharp::test_namespace_is_a_transparent_qualname_container
- tests/test_lang.py::TestCSharp::test_interface_member_is_implicitly_public
- tests/test_lang.py::TestCSharp::test_file_scoped_namespace_is_a_transparent_qualname_container
- tests/test_lang.py::TestCSharp::test_leading_xml_doc_comment_binds_as_doc_text
- tests/test_lang.py::TestCSharp::test_csharp_no_block_comment_type_split
- tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_registered_capabilities_pass
- tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_broken_continuation_fixture_is_caught_not_rubber_stamped
- tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_no_symbols_fixture_is_caught_not_rubber_stamped
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