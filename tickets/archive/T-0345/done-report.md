## Done report

Updated CWE_TOP_25_CATALOG / CWE_TOP_25_OUT_OF_SCOPE / _CWE_TOP_25_IDS in
src/frob/strata/_threat.py from the stale 2023 pin to the actual 2025 MITRE
CWE Top 25 (cross-verified independently by the reviewer against
cwe.mitre.org/top25/archive/2025 -- exact 25-id match, no extras/omissions):
7 ids reused from CWE_CATALOG; 2 new catalog obligations (CWE-94, CWE-639
reusing the sql join); 16 OutOfScopeEntry rows including the 6 named
untranscribed ids (CWE-120/121/122 buffer-overflow trio, CWE-284, CWE-770,
CWE-200). The 6 ids dropped from the 2025 list handled correctly (CWE-798
retained in CWE_CATALOG since cited elsewhere, removed only from the top25
tuples; CWE-287/190/119/362/269/276 OutOfScope rows removed).

CWE-200 reconciled to out_of_scope:authn-authz-boundary-predicate to MATCH
docs/design/registry/weaknesses.yaml's existing judgment rather than
silently contradict it (single-source-of-truth discipline).

Evidence (3 ids, all pass; reviewer confirmed non-tautological -- assert
real reason substrings / capability_kind identity / catalog membership):
TestCweTop25::test_cwe_200_matches_the_weaknesses_registrys_own_disposition,
::test_buffer_overflow_trio_name_the_same_missing_bounds_model,
::test_cwe_639_reuses_the_sql_capability_join. Litmus fixtures cwe_89_*.strata
reused for CWE-639 with disclosed rationale. Reviewer APPROVED.

Landed via 3-way patch onto current main (worktree stale). No REL bump: the
catalog is internal data, no public-API surface change (release check green).
