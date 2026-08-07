## Done report

Added `_PII012_REVIEWED_NON_PII` (a reviewed (rel_path, identifier-text)
disposition table, T-0540) plus `_is_pii012_reviewed_non_pii`, wired into
both `_scan_identifier_keywords` and `_scan_comment_keywords`. Every one
of the 69 unique (file, identifier) pairs behind the 102-finding residual
was individually read at its call site before being added (lexer/parser/
AST/git-ref/shell-command/LLM-context "token" homonyms in frob's own
tooling; this codebase's own std.secrets declaration-construct "secret"
homonym; a handful of single-site homonyms: passwd/passwd_added/
passwd_removed raw /etc/passwd text, run_diagnosis/test_run_diagnosis_*
frob-doctor feature name, email docstring example, _cve_fingerprint_scan
module-name prose, password CWE-catalog title string).

`FIELD_SIGNATURES` itself was NOT narrowed for "token"/"secret" -- it is
still shared with PII010's field scan, where a field genuinely named
token/secret on a real data structure must stay deny-by-default. This
table exempts PII012's weaker identifier/comment signal only, matched on
identifier text (not line number), so a refactor that only shifts lines
does not silently widen the exemption to a genuinely new identifier.

`uv run frob check --only pii_structural`: PII012 findings went from 102
to 0 (gate:PII: 0 errors, 0 warnings, 3 waived -- unrelated pre-existing
PII011 waivers). PII010/SEC110 counts unaffected (verified same warnings
before/after).

### Changed
```
 src/frob/gates/_pii_structural.py | 167 ++++++++++++++++++++++++++++++++++++--
 tickets.md                        |  50 +++++++++++-
 2 files changed, 208 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_function_parameter_keyword_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_unrelated_identifier_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_tokenizer_identifier_does_not_falsely_match_token` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_data_structure_field_not_double_reported` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_frob_directive_comment_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires` (pytest node id, verified passing when recorded)
