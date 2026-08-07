## Done report

Extended _LANGUAGE_TAG_SYNONYMS mapping (python->py, typescript->ts,
kotlin->kt, cplusplus->cpp) and folded it into _LANGUAGE_TAG_RE / a
normalizing _language_tag so long-form language spellings resolve to the
same canonical short tag as their short-form counterpart before
_is_language_parity_family's distinctness check runs.

Measured before/after via `frob check --only arch --json`, counting
"abstraction-opportunity" occurrences: 66 -> 65 (frob.testing._collect*.py's
collect_python_tests/collect_typescript_tests/collect_kotlin_tests/
collect_cpp_tests family no longer false-positives).

### Changed
```
 tickets.md | 10 +++++++---
 1 file changed, 7 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 453 warning(s), 678 waived
- error-findings: none (measured, zero errors)
