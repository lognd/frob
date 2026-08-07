---
id: T-0129
title: wire .strata into frob.graph/outline/xref/testing/policy/cycle scanners
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/outline/**
- src/frob/xref/**
- src/frob/testing/**
- src/frob/policy/**
- src/frob/app/cycle_runner.py
- src/frob/arch/__init__.py
- src/frob/lang/__init__.py
- tests/unit/test_lang_primitives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_primitives.py::test_supported_extensions_includes_tree_sitter_and_strata
- tests/unit/test_lang_primitives.py::test_tree_sitter_extensions_excludes_strata
- tests/unit/test_lang_primitives.py::test_language_for_extension_covers_every_supported_extension
designated_repro_test: null
threat: null
component: null
---
T-0077 registered .strata as a frob.lang grammar (parse_file/supported_languages), but every consumer of frob.lang filters files through its own hand-maintained extension table/suffix check instead of frob.lang.supported_languages() -- frob.graph's _SOURCE_EXTENSIONS, frob.outline's outline_file suffix dispatch, frob.xref's _SOURCE_EXTS, frob.testing._select's _EXTENSION_LANGUAGE, frob.policy's own table, frob.app.cycle_runner's _PY_EXTS/_CPP_EXTS, and frob.arch's raw_tree call in _analyze_one_file (which has no extension guard at all and calls the tree-sitter-only raw_tree escape hatch on every collected file, including .strata -- this is why 'no grammar registered for extension .strata' warnings for design/litmus/*.strata persist in frob check even after T-0077). None of these are in T-0077's scope (src/frob/lang/**, src/frob/strata/**, tests/**). Add .strata to each table (or route arch's raw_tree call through parse_file with a skip for languages that have no Tree), so map/outline/xref/COV obligations actually reach .strata symbols end to end.

Scope note (implementer, 2026-07-18): widened scope to include src/frob/lang/__init__.py + tests/unit/test_lang_primitives.py. The DRY fix this ticket asks for -- routing every consumer through frob.lang's canonical extension registry instead of seven hand-copied tables -- has no home unless frob.lang exposes one; supported_languages() alone (a label set, no extension) isn't enough. Added three small public functions there: supported_extensions(), tree_sitter_extensions(), language_for_extension() (docs/modules/graph.md#public-api anchors, frob:tests bound in tests/unit/test_lang_primitives.py). Re-run frob ticket sweep T-0129 after this scope edit before closing.
## Done report

Canonical extension registry added to frob.lang (supported_extensions,
tree_sitter_extensions, language_for_extension); three hand-rolled
tables eliminated (graph._SOURCE_EXTENSIONS, testing._select and
policy _EXTENSION_LANGUAGE -- fixing policy's latent .tsx->"tsx"
mismatch that never matched _IMPORT_PATTERNS); arch gates raw_tree on
tree_sitter_extensions so .strata skips silently. outline/xref/
cycle_runner tables kept as documented derivations because frob.lang's
cpp table genuinely lacks .c++/.hxx/.h++ (reviewer-verified). outline
gains a .strata bucket; xref collects .strata via plain-text fallback
with --lang strata. Reviewer approved the code on merits (initial
REJECT was for this missing ledger trail, completed at merge by the
coordinator). Verified at merge: 23 tests in lang-primitives+excludes
suites, full check exit 0.