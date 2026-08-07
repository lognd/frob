---
id: T-1455
title: COV004 attachment check shipped as an unconditional-fire stub
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/strata/_effects.py
- tests/test_gates.py
- .gitattributes
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov004_matching_sha_is_clean
- tests/test_gates.py::TestCoverageGate::test_cov004_missing_attachment
designated_repro_test: null
acceptance:
- text: GIVEN an attachment whose file exists with a byte-exact sha256 WHEN the COV
    gate runs THEN COV004 does not fire
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_cov004_matching_sha_is_clean
- text: GIVEN a missing or content-drifted attachment WHEN the COV gate runs THEN
    COV004 fires
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_cov004_missing_attachment
threat: null
component: null
---
Found 2026-08-02 by the first real frob ticket attach (T-1433 diagnostics): _cov004_one returned a Violation unconditionally -- no existence check, no sha comparison -- so every recorded attachment errored the COV gate even when byte-identical. Only the confirmatory direction (missing file fires) was tested, the exact TEST016 anti-pattern. Fixed: real existence+sha256 comparison, plus the discriminating regression test (matching sha is clean). Also bundled: OPAQUE001 false-positive restructure in strata/_effects.py (frozenset[str]() instantiation matches the container-dynamic-key-call shape; hoisted an annotated empty constant) and a .gitattributes -text pin on tickets/attachments/** so checkout-time CRLF conversion can never invalidate recorded attachment bytes.