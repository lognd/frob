## Done report

Reclassified the 4 non-out_of_scope rows (CMPL-ASVS-CHAPTERS,
CMPL-ASVS-REQUIREMENTS, CMPL-FEDRAMP-IMPACT-TIERS, CMPL-SLSA-BUILD-LEVELS)
from the vacuous handled_by:COMPLIANCE005 self-reference to a documented
(d) out_of_scope disposition: no primary-source leaf-control text is
available per docs/design/compliance-corpus.md's own research-method
caveat to build real per-control enforcement without fabricating it.
Checked for overlap with existing non-compliance gates before classifying
out of scope (ASVS overlaps existing security gates only incidentally --
no direct 1:1 control mapping exists; SLSA build-level attestation has no
existing supply-chain/provenance tooling in this repo to hang a
RegulationEntry off of).

Resumed from an OOM-killed prior session; this session verified the
already-drafted reclassification, ran the full compliance test file, and
merged main forward with no scope regression.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |  43 ++--
 docs/design/registry/compliance.yaml        |  95 +++++---
 docs/modules/gates.md                       |  33 ++-
 docs/strata/threat.md                       |  11 +
 src/frob/gates/_sys.py                      | 124 +++++++++-
 src/frob/strata/_compliance.py              |  40 +++-
 tests/test_gates.py                         |  76 ++++++
 tests/unit/strata/test_compliance.py        |  22 +-
 tickets.md                                  | 352 ++++++++++++++++++++++++++--
 9 files changed, 709 insertions(+), 87 deletions(-)
```

### Evidence
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 394 warning(s), 678 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py
