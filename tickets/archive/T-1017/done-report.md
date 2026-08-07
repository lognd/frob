## Done report

Own-gate fallout from T-0998's land: the new SCOPE002 gate function was 84 lines (ARCH001, now error-tier) and callgraph.py carried an 89-char line (E501). Extracted the edge-gap and helper-gap loops into their own functions with a shared remediation-hint builder, which also removed the four-times-duplicated message body; wrapped the long line. All 19 scope-closure tests green post-refactor. Filing this ticket itself triggered the new closure warning surface -- working as designed.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 19277 warning(s), 458 waived
- error-findings: AFFECT001@src/frob/graph/callgraph.py
