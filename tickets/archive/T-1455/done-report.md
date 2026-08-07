## Done report

Coordinator-inline fix during the drain drive. _cov004_one shipped as an
unconditional-fire stub (no existence check, no sha comparison), exposed
by the drive's first real frob ticket attach (T-1433 diagnostics). Only
the confirmatory direction was ever tested -- the TEST016 anti-pattern
in the gate that exists to catch it. Now: byte-exact sha256 comparison,
missing-or-drifted fires, matching stays silent, both directions tested.
Bundled: OPAQUE001 false-positive restructure in strata/_effects.py
(frozenset[str]() matches the container-dynamic-key-call shape) and a
.gitattributes -text pin on tickets/attachments/** so autocrlf can never
invalidate recorded attachment bytes.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov004_matching_sha_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov004_missing_attachment` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1954 warning(s), 729 waived
- error-findings: none (measured, zero errors)
