---
id: T-0405
title: 'Language extension contract: one typed registration per language + conformance
  gate that fails on any missing facet'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/lang/
- src/frob/vet/
- src/frob/testing/
- src/frob/arch/
- src/frob/gates/
- tests/test_lang_support.py
- tests/test_lang_conformance_gate.py
- docs/modules/lang.md
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_lang_support.py
  reason: conformance model needs its own test files, doc anchor section, and the
    REL001-driven version bump/lockfile/release-stamp fallout
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: conformance model needs its own test files, doc anchor section, and the
    REL001-driven version bump/lockfile/release-stamp fallout
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/lang.md
  reason: conformance model needs its own test files, doc anchor section, and the
    REL001-driven version bump/lockfile/release-stamp fallout
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: conformance model needs its own test files, doc anchor section, and the
    REL001-driven version bump/lockfile/release-stamp fallout
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: conformance model needs its own test files, doc anchor section, and the
    REL001-driven version bump/lockfile/release-stamp fallout
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: conformance model needs its own test files, doc anchor section, and the
    REL001-driven version bump/lockfile/release-stamp fallout
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_lang_support.py::TestDeriveLanguageRegistry::test_covers_every_supported_language
- tests/test_lang_support.py::TestConformanceViolations::test_missing_facet_fails
- tests/test_lang_support.py::TestConformanceViolations::test_fully_registered_language_passes
- tests/test_lang_support.py::TestConformanceViolations::test_unreasoned_known_gap_fails
- tests/test_lang_conformance_gate.py::TestLangConformanceGate::test_real_registry_is_clean
- tests/test_lang_conformance_gate.py::TestLangConformanceGate::test_missing_facet_becomes_error_violation
designated_repro_test: null
threat: null
component: null
---
User directive (2026-07-20): adding a new language/capability (Kotlin, Swift/iOS native, Go, ...) must be VERY simple -- one well-defined registration, not a scattered edit across 10 files where forgetting one silently creates a coverage gap (the exact fail-open per-language holes the audit found: Python is binding-resolved while TS/Rust/C++ are lexical; doc/cov/drift gates run only in the Python pipeline). SOLUTION couples easy-extension with no-silent-gaps: define a LanguageSupport protocol/registry enumerating EVERY per-language facet frob needs -- tree-sitter grammar + extension map, comment-span extraction, capability pattern table, binding-aware capability RESOLVER (import/alias/scope), dangerous-operation registry entries, CVE fingerprint support, obfuscation/bidi scanning, test runner, arch complexity detectors, dup normalization, doc/directive parsing. Each registered language declares, per facet, either an implementation OR an explicit reasoned not-applicable. Then a CONFORMANCE GATE (fail-closed, like strata SYS/threat exhaustiveness) enumerates languages x facets and FAILS the build if any registered language is missing any facet with no reasoned n/a -- so a half-added language cannot ship, and the current TS/Rust/C++ lexical gaps show up immediately as conformance failures. Acceptance: adding a fixture language that implements the grammar+runner but omits the resolver FAILS the conformance gate naming the missing facet; a fully-implemented language passes; adding Kotlin/Swift is demonstrably a single registration + the facet impls the gate demands, nothing else. This is the structural prevention for the whole per-language-gap class; ties to T-0400 (vet resolution) and T-0404 (polyglot enforcement) which become "make every language conform".