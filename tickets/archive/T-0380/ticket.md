---
id: T-0380
title: 'vet: extend binding-aware resolution into CVE fingerprint scanning'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0377
- T-0378
- T-0379
parent: T-0376
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: 'playbook mandate: update docs/modules/vet.md in the same change as src/frob/vet/_capability.py''s
    new public-api entries (T-0380 fingerprint binding resolution)'
  actor: logan
  at: '2026-07-28'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 478
  new_length: 1730
evidence:
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_python_aliased_pickle_loads_still_matches
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_python_unaliased_control_still_matches_lexically
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_typescript_aliased_require_still_matches
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_typescript_clean_source_does_not_match
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_rust_aliased_use_still_matches
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_rust_clean_source_does_not_match
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_c_aliased_macro_still_matches
- tests/vet_suite/test_fingerprint.py::TestFingerprintBindingResolution::test_c_clean_source_does_not_match
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
_scan_file_fingerprints (CVE matching) is lexical needle-matching for EVERY language including Python -- a renamed import defeats a fingerprint even where capability scanning is binding-aware. Reuse the binding tables built for capability resolution (Python + the new TS/Rust/C-C++ tables) to resolve aliases before fingerprint matching for all languages. Acceptance: an aliased import that would evade a lexical fingerprint match is still caught; adversarial test per language.

T-4718 sweep (condensed from src/frob/vet/_capability_scan.py:305-326,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# The CVE-fingerprint sibling of `_scan_file_operations` (T-0153): a
# fingerprint's `language` must match `path`'s scanned language bucket AND
# at least one of its `needles` must appear in the file's text, the SAME
# recall-over-precision substring philosophy `_matched_capabilities`
# already uses (module docstring). Imports `frob.strata` LAZILY (not at
# module scope): `frob.strata._effects` imports THIS module for its own
# `_PATTERNS`/`language_for` join, so a top-level `frob.strata` import
# here would be a genuine import cycle -- deferred until call time, when
# both packages have finished initializing.
#
# T-0380: lexical needle-matching alone lets an aliased import evade a
# fingerprint (`import pickle as p; p.loads(...)` never contains the
# literal text `pickle.loads(`) even where capability scanning is already
# binding-aware for the same module. `_binding_fingerprints` folds in
# every fingerprint the file's binding tables resolve to, unioned with the
# existing lexical result by `id` (a fingerprint caught either way is
# reported once, not twice).