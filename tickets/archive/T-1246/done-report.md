## Done report

CMPL-GDPR-ARTICLES was carrying the vacuous handled_by:COMPLIANCE005
self-reference, not riding the 3 real GDPR-ERASURE/GDPR-RETENTION/
GDPR-LAWFUL-BASIS RegulationEntry units already in COMPLIANCE_CATALOG --
reclassified (d) out of scope: no primary-source article-level control
text available per docs/design/compliance-corpus.md's own research-method
caveat.

Re-reviewed COMPLIANCE_OUT_OF_SCOPE's CCPA entry per T-1242's landed
exposure:public-web + T-1314's landed PRIVACY-NOTICE RegulationEntry
(privacy_policy_attestation). Narrowed rather than retired: CCPA remains
out of scope for right-to-delete (no CA-specific request-tracking
primitive in the kernel, still caught only by PII010's structural
fallback), but PRIVACY-NOTICE now directly discharges the right-to-know/
notice-at-collection component (both are the same "must disclose what is
collected" duty; PRIVACY-NOTICE's RegulationEntry cite already names CCPA
Sec.1798.100 as a see-also). review date extended to 2027-07-29. Also
documented this narrowing in docs/strata/threat.md (AFFECT001's
affects()-closure obligation on COMPLIANCE_OUT_OF_SCOPE, satisfied while
closing the sibling T-1314).

Resumed from an OOM-killed prior session; this session verified the
already-drafted reclassification, ran the full compliance test file, and
merged main forward with no scope regression.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |  43 +++---
 docs/design/registry/compliance.yaml        |  95 +++++++-----
 docs/modules/gates.md                       |  33 +++-
 docs/strata/threat.md                       |  11 ++
 src/frob/gates/_sys.py                      | 124 +++++++++++++++-
 src/frob/strata/_compliance.py              |  40 ++++-
 tests/test_gates.py                         |  76 ++++++++++
 tests/unit/strata/test_compliance.py        |  22 ++-
 tickets.md                                  | 223 +++++++++++++++++++++++++---
 9 files changed, 580 insertions(+), 87 deletions(-)
```

### Evidence
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 395 warning(s), 678 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py
