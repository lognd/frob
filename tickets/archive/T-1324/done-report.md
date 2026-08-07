## Done report

Corrected docs/design/compliance-corpus.md's FROB-CATALOG-ENTRIES manifest
row (count 6 -> 7) and TOTAL_LEAF_CONTROLS_ENUMERATED (599 -> 600) to match
the 7th RegulationEntry (PRIVACY-NOTICE) T-1314 added to COMPLIANCE_CATALOG,
matching the already-corrected docs/design/registry/compliance.yaml row
from T-1250. Updated the sum's inline arithmetic breakdown (frob-existing
6 -> 7) to match.

### Changed
```
 docs/design/compliance-corpus.md | 8 ++++----
 tickets.md                       | 3 +--
 2 files changed, 5 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 155 warning(s), 749 waived
- error-findings: PRE001@tickets/T-1324, REG005@docs/design/registry/check-coverage.yaml, REG007@docs/design/registry/check-coverage.yaml
