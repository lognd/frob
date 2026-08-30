---
id: T-1601
title: 'Language support: Java'
state: done
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
- src/frob/lang/_walk_java.py
- tests/fixtures/lang/**
- tests/test_lang.py
- tests/test_lang_conformance_gate.py
- tests/test_lang_support.py
- docs/modules/lang.md
- src/frob/lang/_extract.py
- src/frob/lang/__init__.py
- src/frob/lang/_support.py
- src/frob/gates/_lang_conformance.py
- frob.toml
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
  glob: src/frob/lang/_walk_java.py
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
  reason: central walker/import-walker dispatch table must register java, same as
    every prior language adapter (T-1600/T-1604 precedent)
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/lang/__init__.py
  reason: extension table must map .java to the java grammar, same as every prior
    adapter
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/lang/_support.py
  reason: adapter capability/conformance registry needs a java LanguageSupport entry,
    same as T-1600/T-1604
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_lang_conformance.py
  reason: LANG004 capability-conformance fixture + gate wiring for the new java adapter,
    same as T-1600/T-1604
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.toml
  reason: test.runner entry routing .java fixture data through the pytest suite instead
    of collected as a test file, same shape as the T-1600 csharp entry
  actor: logan
  at: '2026-08-30'
evidence:
- tests/test_lang.py::TestJava::test_walks_class_and_method
- tests/test_lang.py::TestJava::test_package_private_method_is_not_public
- tests/test_lang.py::TestJava::test_private_method_is_not_public
- tests/test_lang.py::TestJava::test_static_final_field_is_a_const_symbol
- tests/test_lang.py::TestJava::test_plain_field_is_not_extracted
- tests/test_lang.py::TestJava::test_enum_is_a_class_symbol
- tests/test_lang.py::TestJava::test_inner_class_is_a_transparent_qualname_container
- tests/test_lang.py::TestJava::test_interface_member_is_implicitly_public
- tests/test_lang.py::TestJava::test_interface_default_method_is_implicitly_public
- tests/test_lang.py::TestJava::test_leading_javadoc_comment_binds_as_doc_text
- tests/test_lang.py::TestJava::test_java_two_comment_node_types
- tests/test_lang.py::TestJava::test_import_declaration_is_extracted
- tests/test_lang.py::TestJava::test_multiple_declarators_in_one_field_declaration
- tests/test_lang_conformance_gate.py::TestJavaCapabilityConformance::test_java_registered_capabilities_pass
- tests/test_lang_conformance_gate.py::TestJavaCapabilityConformance::test_java_broken_continuation_fixture_is_caught_not_rubber_stamped
- tests/test_lang_conformance_gate.py::TestJavaCapabilityConformance::test_java_no_symbols_fixture_is_caught_not_rubber_stamped
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e030f5ed39711ee40323c3614f8e717eb217c349
---
Add Java to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: Package-private as the default visibility (no keyword) is the trap -- absence of a modifier is meaningful. Inner and anonymous classes, interfaces with default methods, annotations, and Javadoc as the doc-comment form. One public class per file is a convention frob can exploit for node ids.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.