---
id: T-1603
title: 'Language support: Zig'
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
- src/frob/lang/_walk_zig.py
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
  glob: src/frob/lang/_walk_zig.py
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
evidence:
- tests/test_lang.py::TestZig::test_walks_top_level_function
- tests/test_lang.py::TestZig::test_function_without_pub_is_not_public
- tests/test_lang.py::TestZig::test_struct_and_method
- tests/test_lang.py::TestZig::test_enum_is_a_type_symbol
- tests/test_lang.py::TestZig::test_top_level_const_is_a_const_symbol
- tests/test_lang.py::TestZig::test_error_union_return_type_is_captured_in_signature
- tests/test_lang.py::TestZig::test_triple_slash_doc_comment_binds_as_doc_text
- tests/test_lang.py::TestZig::test_plain_comment_does_not_bind_as_doc_text
- tests/test_lang.py::TestZig::test_comptime_block_is_not_walked_for_symbols
- tests/test_lang.py::TestZig::test_zig_two_comment_node_types
- tests/test_lang.py::TestZig::test_import_builtin_is_extracted
- tests/test_lang_conformance_gate.py::TestZigCapabilityConformance::test_zig_registered_capabilities_pass
- tests/test_lang_conformance_gate.py::TestZigCapabilityConformance::test_zig_broken_continuation_fixture_is_caught_not_rubber_stamped
- tests/test_lang_conformance_gate.py::TestZigCapabilityConformance::test_zig_no_symbols_fixture_is_caught_not_rubber_stamped
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add Zig to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: pub as the explicit visibility marker, comptime blocks, error unions in signatures, and doc comments (triple-slash) distinct from ordinary comments. Zig has no macro preprocessor, which makes it a cleaner symbol-extraction target than C/C++ -- a good early probe of whether the contract is genuinely language-agnostic.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.