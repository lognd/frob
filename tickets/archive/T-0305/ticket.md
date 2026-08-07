---
id: T-0305
title: 'typescript ffi scanner: word-boundary napi match, fixes openapi false positive
  (graphite T-0019)'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry.py
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_capability_registry.py::TestNegativeFixtures::test_openapi_generated_ts_is_not_ffi
- tests/test_capability_registry.py::TestNegativeFixtures::test_real_napi_import_still_fires_ffi
- tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_pre_registry_needle_still_fires_somewhere
- tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_reclassified_needle_actually_still_fires_under_its_new_kind
designated_repro_test: null
acceptance:
- text: scan_file_capabilities does not report ffi for source containing only the
    word openapi/OpenAPI (no real node-ffi/ffi-napi usage)
  evidence: []
- text: scan_file_capabilities still reports ffi for a real napi-based native addon
    import
  evidence: []
threat: null
component: null
---
graphite's frob-adoption sweep found SYS100 firing on capability ffi for node browser sourced from frontend/src/api/api.generated.ts and client.ts -- both openapi-typescript codegen with zero real FFI. Root cause: the bare substring needle 'napi' also matches inside the ordinary word 'openapi' (o-p-e-n-[napi]). Fixed by moving 'napi' out of the plain needle table into an identifier-boundary special check (_has_word_boundary_napi, mirroring the existing T-0151 _has_bare_compile_call precedent for the same needle-is-a-substring-of-an-unrelated-word bug class), plus a regression test using the graphite api.generated.ts fixture shape verbatim.