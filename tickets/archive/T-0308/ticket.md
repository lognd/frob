---
id: T-0308
title: capability scanner matches inside comments/strings + unbounded substrings (net,
  ffi/napi)
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
- tests/test_vet.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
- tests/test_capability_registry.py::TestNegativeFixtures::test_openapi_generated_ts_is_not_ffi
- tests/test_capability_registry.py::TestNegativeFixtures::test_real_napi_import_still_fires_ffi
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (graphite, aprog-public): scan_file_capabilities pattern-matches over comment/string text, not just executable code, and uses unbounded substring matches. (1) net/fetch_url fired from a '# ...requests.get(url)...' COMMENT in aprog-public starter.py (no real net call). (2) ffi fired on the plain word 'openapi' because the ffi needle is a bare substring 'napi' (o-p-e-n-napi) in openapi-typescript codegen. Both forced repos to declare capabilities they don't have + discharge bogus CWE obligations via assume/waive. Fix: (a) give the scanner comment/string awareness (do not match inside #-comments / string literals where the language allows cheap detection), (b) word-boundary the needles (napi, etc.). Litmus per needle: a commented-out requests.get and the word openapi must NOT fire.