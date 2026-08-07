## Done report

T-1241's acceptance ("is CCPA/GDPR notice enforced -> a named
RegulationEntry+mitigation+test+gate, not a disposition string") is
already fully satisfied by prior landed tickets (T-1242 exposure:public-web
vocabulary, T-1314 PRIVACY-NOTICE RegulationEntry, T-1244-1250 re-triage of
the 27-row corpus, T-1246 CCPA out-of-scope narrowing). Verified live on
this worktree, not re-derived from prose:

- docs/design/registry/compliance.yaml carries exactly 27 CMPL-* rows:
  26 now reasoned out_of_scope:... dispositions (paywalled/process/
  advisory classification per T-1245-T-1249 triage, each naming a real
  caught_by), 1 handled_by:COMPLIANCE005 meta-row (CMPL-FROB-CATALOG-
  ENTRIES) explicitly documented as verified via COMPLIANCE_CATALOG's own
  real RegulationEntry units, not a vacuous disposition string.
- COMPLIANCE_CATALOG (src/frob/strata/_compliance.py) now carries 7
  RegulationEntry/mitigation pairs (COPPA, GDPR-ERASURE/RETENTION/BASIS,
  HIPAA-BAA, MINIMIZATION, PRIVACY-NOTICE), each backed by a real
  structural predicate in check_regulation_discharge (_check_privacy_notice
  for PRIVACY-NOTICE: an exposure:public-web-tagged Pii-or-above node
  with no privacy-policy attr fires COMPLIANCE002, node-level, not a
  disposition string).
- exposure:public-web attr vocabulary (_EXPOSURE_PREFIX, _has_exposure)
  now exists and is consumed by _check_privacy_notice, closing the exact
  gap named in this ticket's filing note.
- CCPA/CPRA's OutOfScopeRegulation entry is narrowed (T-1246): right-to-
  know is no longer wholly out of scope (PRIVACY-NOTICE covers it directly);
  right-to-delete remains the honest residual gap, caught_by PII010.

No code change was needed in this session -- this ticket's own concrete
example (exposure:public-web forcing a privacy-policy mitigation) was
already built and gated by T-1314/T-1242, and the 27-row corpus was
already re-triaged off vacuous COMPLIANCE005 self-reference by
T-1245-T-1249/T-1250. Closing on verified evidence rather than force-
extending scope to redo already-landed work.

Changed: none (no code touched; ticket closes on verification of prior
landed work against its own acceptance criterion)
Evidence:
  tests/unit/strata/test_compliance.py (74 passed)
  tests/test_gates.py -k Compliance (14 passed)
  uv run frob check --ticket T-1241 --only compliance --json:
    gate-summary 0 errors, 0 warnings, 0 waived
Filed: none
Gates: frob check --ticket T-1241 --only compliance clean (0/0/0);
  gates-native scoped run also clean for this file set (ARCH 0 warnings)

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 258 warning(s), 745 waived
- error-findings: none (measured, zero errors)
