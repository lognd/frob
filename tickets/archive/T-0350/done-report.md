## Done report

Changed:
- src/frob/gates/_pii_structural.py: new PII012 rule (T-0350 family 5,
  keyword sweep at suggestion severity). `_scan_identifier_keywords` walks
  plain identifiers (variable Store-context names, function parameters,
  function/async-function def names) matching `FIELD_SIGNATURES`,
  excluding sites `_scan_python_fields`/PII010 already reports on so the
  same field is never double-reported under two rule ids;
  `_scan_comment_keywords` extracts `#`-comment word tokens (regex
  tokenizer, not a value-shape ban -- family 4's non-regex mandate is
  specific to email-shape matching) and matches them the same way;
  `_scan_python_keyword_sweep` combines both, wired into
  `pii_structural_gate`. Fires at WARN ("suggestion") severity, the
  ticket body's explicit "no hard fail on names alone".
- tests/test_pii_structural_gate.py: new `TestKeywordSweep` class (6
  cases): identifier fires at WARN, function-parameter fires, comment
  keyword fires, unrelated identifier does not fire, `tokenizer` does not
  falsely match `token` (T-0219-style whole-token discipline), and a
  PII010-covered dataclass field is NOT double-reported under PII012.
- docs/modules/gates.md: documented PII012 in the rule table and the
  "Structural PII secrets detection T-0207" section.

Evidence:
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_function_parameter_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_unrelated_identifier_does_not_fire
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_tokenizer_identifier_does_not_falsely_match_token
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_data_structure_field_not_double_reported
- Full-file run: `uv run pytest tests/test_pii_structural_gate.py tests/test_secrets_gate.py -q` -> 90 passed
- `uv run frob test --base main` -> [PASS] python exit=0
- `uv run frob check --delta --ticket T-0350` -> gates 0 errors, 296 new
  WARN (identifier/comment keyword hits across the existing repo's own
  source -- expected at suggestion severity, none ERROR, `frob check`
  stays green)

Caveat: an early pass had `ty` flag `_scan_identifier_keywords`'s
`already_covered` set-comprehension (`node.lineno` on a bare `ast.AST` the
type checker can't narrow through a bool-returning helper) -- fixed by
inlining the `isinstance(node, ast.AnnAssign)` check directly in the
comprehension so the narrowing is visible to `ty`. `uv run ty check` is
clean now.

Filed: none this ticket (T-0455 scope-narrowing bug already corrected
under T-0348's Done report, applies identically here).

Gates: `uv run frob check --delta --ticket T-0350` clean (0 errors). ruff
check/format and ty both clean.

### Changed
```
 docs/modules/gates.md             |  31 ++++-
 src/frob/gates/_pii_structural.py | 283 ++++++++++++++++++++++++++++++++++++--
 tests/test_pii_structural_gate.py | 134 ++++++++++++++++++
 tickets.md                        | 182 +++++++++++++++++++++++-
 4 files changed, 611 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_function_parameter_keyword_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_unrelated_identifier_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_tokenizer_identifier_does_not_falsely_match_token` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_data_structure_field_not_double_reported` (pytest node id, verified passing when recorded)
