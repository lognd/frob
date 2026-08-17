---
id: T-2069
title: PII012 over-matches the bare word 'token' as credentials category-wide
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_pii.py
- src/frob/gates/**pii**
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: add repro/fix test coverage for PII012 bare-word 'token' over-match fix
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_cli_argv_tokenizer_parameter_does_not_fire
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[compound-api_token]
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[bare-token]
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_comment_with_no_value_shape_does_not_fire
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_comment_with_value_shape_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_matching_in_scope_identifier_fires
designated_repro_test: tests/test_pii_structural_gate.py::TestTokenValueGating::test_cli_argv_tokenizer_parameter_does_not_fire
evidence_changes:
- old_node: tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires
  new_node: tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[compound-api_token]
  reason: 'T-2069: parametrized to dedupe with the bare-token case (DUP002)'
  actor: logan
  at: '2026-08-10'
- old_node: tests/test_pii_structural_gate.py::TestTokenValueGating::test_bare_token_assigned_a_string_literal_still_fires
  new_node: tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[bare-token]
  reason: 'T-2069: parametrized to dedupe with the compound-token case (DUP002)'
  actor: logan
  at: '2026-08-10'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured on current main via `uv run frob check --only pii_structural
--json` (T-2032's post-fix PII012 investigation, this ticket filed while
fixing 3 findings on `src/frob/testing/_coverage_refresh.py`).

PII012's keyword-sweep flags any identifier/comment word containing
'token' as category 'credentials', with no distinction between "a
CLI/lexical argv token" (this repo's overwhelmingly common usage: pytest
argv tokens, ticket-parsing tokens, doc-anchor tokens) and an actual
secret/credential token. Repo-wide count at time of filing:

  27 PII012 findings citing 'matches token' (name), across 9 distinct
  files: src/frob/arch/_abstraction.py, src/frob/gates/_docptr.py,
  src/frob/gates/_tickets_gate.py, src/frob/gates/_todo_fmt.py, and
  5 more (full list in the --json dump this ticket cites as evidence
  context -- not re-pasted here to keep this body short).

None of the 3 examined directly (this file, `_tickets_gate.py`,
`_docptr.py`) refer to a credential -- all are lexical/CLI/doc-anchor
tokens. This does not prove all 27 are false positives (not individually
audited here), but the category is clearly over-broad for the bare word
'token' specifically.

Do NOT weaken PII012 globally or add a blanket exemption -- per this
repo's own T-1967 lesson, an exemption matching the normal case disables
the guard. Options worth considering instead: a narrower keyword-vs-value
heuristic (only flag 'token' adjacent to an actual string-literal
assignment, not a bare identifier/comment name), or moving 'token' out of
the 'credentials' category into its own lower-severity or context-gated
category. Left to the assignee to design; this ticket exists to record
the measured breadth so a future waiver-spree isn't mistaken for evidence
of a real defect count.

## Done report

Changed:
- src/frob/gates/_pii_structural/_keywords.py::_VALUE_GATED_KEYWORDS
- src/frob/gates/_pii_structural/_keywords.py::_TOKEN_VALUE_SHAPE_RE
- src/frob/gates/_pii_structural/_keywords.py::_requires_value_evidence
- src/frob/gates/_pii_structural/_keywords.py::_token_literal_assignment_target_ids
- src/frob/gates/_pii_structural/_keywords.py::_scan_identifier_keywords
- src/frob/gates/_pii_structural/_keywords.py::_scan_comment_keywords
- tests/test_pii_structural_gate.py::TestTokenValueGating (new)
- tests/test_pii_structural_gate.py::TestKeywordSweep.test_standalone_comment_matching_in_scope_identifier_fires (fixture swapped token -> secret; extended to avoid DUP001)

Measured denominator (before fixing anything, `frob check --only pii_structural --json`, current main tip at ticket start):
- 4 unwaived PII012 ERROR findings repo-wide, all in src/frob/testing/_coverage_refresh.py (lines 709, 710, 714, 744), all bare word "token" -- 3 standalone comments ("value token" / "distribution-mode ... token" x2) and 1 loop variable (`for token in tokens:`). All 4 are genuinely non-credential (pytest-xdist CLI argv tokenizer).
- 0 genuine credential-shaped PII012 hits measured in the current unwaived population -- the other ~20 PII012 keyword-sweep hits on "token"/"secret"/"address"/"diagnosis" that still surface in a full scan are all already downgraded to severity=note by pre-existing per-site `frob:waive` comments (T-0540/T-0971's reviewed-non-PII table), none are errors.

Fix: narrowed PII012 (not PII010/FIELD_SIGNATURES, module docstring's existing "deny-by-default" discipline for the shared registry is untouched) so the "token" keyword specifically requires VALUE evidence before firing:
- identifier hit: only fires if the name is a Store-context assignment target literally bound to a string-Constant value (`_token_literal_assignment_target_ids`, covers Assign and AnnAssign) -- a function name, bare parameter, or loop variable named "token"/"tokens" no longer fires on name alone.
- comment hit: only fires if the comment text itself matches a literal-value-assignment shape (`_TOKEN_VALUE_SHAPE_RE`, e.g. `token = "..."`) -- ordinary prose mentioning "token" no longer fires.
- Every other FIELD_SIGNATURES keyword (password, secret, api_key, ssn, ...) keeps its existing name-only PII012 signal unchanged; this is a targeted narrowing of one measured-over-broad keyword, not a blanket weakening (T-1967's lesson).

Cleared the 4 `_coverage_refresh.py` findings as a consequence of the detector change -- no renaming (the T-2032 rename that regressed is exactly what this ticket says not to repeat), no file/site exemption for that file, and `_strip_xdist_tokens` is untouched.

Evidence:
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_cli_argv_tokenizer_parameter_does_not_fire (DESIGNATED REPRO -- confirmed FAILED_AT_PARENT at 7d12fe873, the test-only commit, via `frob ticket evidence --check-repro`)
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[compound-api_token]
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[bare-token]
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_comment_with_no_value_shape_does_not_fire
- tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_comment_with_value_shape_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_matching_in_scope_identifier_fires

pytest run: `uv run pytest tests/test_pii_structural_gate.py -o addopts="" -q` -> 113 passed.

Filed: none -- no out-of-scope defects found; the DUP001/DUP002 findings frob check --land-parity caught were in my own new test code and fixed in-scope.

Gates:
- `frob check --only pii_structural --ticket T-2069` -- 0 errors, 1 warning (unrelated PII011 elsewhere), 78 waived; zero PII012 findings of any severity for src/frob/testing/_coverage_refresh.py (confirmed by reading the JSON dump, only unrelated SEC110 notes remain for that file).
- `frob check --land-parity` -- clean, 0 unscoped errors (after fixing E501 and DUP001/DUP002 it first caught).
- `frob ticket evidence T-2069 --check-repro` (against 7d12fe873) -- FAILED_AT_PARENT, genuine repro.

### Changed
```
 src/frob/gates/_pii_structural/_keywords.py | 75 ++++++++++++++++++++++
 tests/test_pii_structural_gate.py           | 97 +++++++++++++++++++++++++++--
 tickets/T-2069/ticket.md                    | 29 ++++++++-
 3 files changed, 193 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestTokenValueGating::test_cli_argv_tokenizer_parameter_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[compound-api_token]` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_assigned_a_string_literal_still_fires[bare-token]` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_comment_with_no_value_shape_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestTokenValueGating::test_token_comment_with_value_shape_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_matching_in_scope_identifier_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2069
