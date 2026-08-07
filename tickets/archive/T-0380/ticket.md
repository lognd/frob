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
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: 'playbook mandate: update docs/modules/vet.md in the same change as src/frob/vet/_capability.py''s
    new public-api entries (T-0380 fingerprint binding resolution)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestFingerprintBindingResolution::test_python_aliased_pickle_loads_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_python_unaliased_control_still_matches_lexically
- tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_aliased_require_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_clean_source_does_not_match
- tests/test_vet.py::TestFingerprintBindingResolution::test_rust_aliased_use_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_rust_clean_source_does_not_match
- tests/test_vet.py::TestFingerprintBindingResolution::test_c_aliased_macro_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_c_clean_source_does_not_match
designated_repro_test: null
threat: null
component: null
---
_scan_file_fingerprints (CVE matching) is lexical needle-matching for EVERY language including Python -- a renamed import defeats a fingerprint even where capability scanning is binding-aware. Reuse the binding tables built for capability resolution (Python + the new TS/Rust/C-C++ tables) to resolve aliases before fingerprint matching for all languages. Acceptance: an aliased import that would evade a lexical fingerprint match is still caught; adversarial test per language.