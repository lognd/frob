## Done report

T-1411 round 2 (coordinator correction): acceptance[0] as originally
written asked for the wrong distinction. The two pre-existing tests
flagged as "now regressing" in the first Done report were NOT obsolete --
"x = 1  # stores the user ssn for lookup" is exactly the poorly-named-
variable-holding-PII case PII012 exists to catch: the identifier `x`
matches nothing, and the COMMENT is the only place the datum is named.
Gating every comment uniformly on in-scope-identifier/reference-form (the
round-1 fix) silenced that case -- a real capability regression under the
repo owner's "never remove capability, narrow aim only" constraint.

Refined rule, implemented in src/frob/gates/_pii_structural/_keywords.py:

WHETHER THE COMMENT IS ANNOTATING DATA is now the discriminator, not
"does the word match an identifier in scope":

  - `_extract_comments` (LEVEL 1, tokenize-based, unchanged from round 1)
    now also reports `is_trailing`: True when real source text (not just
    whitespace) precedes the `#` on its physical line.
  - A TRAILING comment (`x = 1  # stores the user ssn`) is annotating the
    statement it follows -- it fires unconditionally on a keyword match,
    exactly as the pre-fix grep did. Both pre-existing tests
    (`test_comment_keyword_fires`, `test_ordinary_comment_mentioning_
    secret_still_fires`) now pass UNCHANGED -- verified, no edits made to
    either.
  - A STANDALONE comment (its own line, nothing but whitespace before the
    `#`) is discussion, not an annotation of a specific datum -- LEVEL 2's
    gate (in-scope identifier token match, or backticked/dotted reference
    form) applies to it alone. The real incident this ticket exists for
    (a standalone multi-line design-rationale comment inside a function
    body, naming no in-scope identifier) is exactly this case and no
    longer fires.

Regression tests added to tests/test_pii_structural_gate.py::
TestKeywordSweep (scope now includes this file; T-1235's earlier tests/**
lease was released and re-registered):
  - test_standalone_prose_comment_with_no_referenced_identifier_does_not_fire
    (acceptance[0])
  - test_standalone_comment_in_reference_form_naming_real_field_fires and
    test_standalone_comment_matching_in_scope_identifier_fires, plus the
    two UNCHANGED pre-existing trailing-comment tests (acceptance[1])
  - test_hash_inside_string_literal_is_not_treated_as_comment
    (acceptance[2])
All 12 tests in TestKeywordSweep pass; the full file (108 tests) passes.

Measured PII012/PII010 combined gate:PII counts via `uv run frob check
--only pii_structural` (repo-wide, 0 errors/0 warnings before and after --
every hit is either a true positive or already reason-waived), comparing
main's untouched original file against this fix:
  before: gate:PII  0 errors, 0 warnings, 40 waived
  after:  gate:PII  0 errors, 0 warnings, 32 waived
Same delta as round 1 (8 fewer PII012 hits) -- the standalone-vs-trailing
refinement does not reintroduce any of the false positives round 1
eliminated (none of this repo's real false-positive hits were trailing
comments), while restoring full capability for the trailing-comment case
the refinement was written to protect.

_PII012_REVIEWED_NON_PII (T-0540) was left untouched, same as round 1:
shrinking it needs a dedicated pass re-running every entry against the
new scanner now that it has real test coverage to protect against
regressions; not attempted this round to keep the fix reviewable.

Ledger note: c46abf91's earlier merge (round 1, before this correction)
took "ours" wholesale for T-1235's ticket block during a splice (because
T-1411's own state was also touched on the same merge), silently
reverting T-1235's already-landed in-progress -> queued requeue. Caught
and repaired in a separate commit (diffed against main's current
tickets.md, confirmed only the `state:` field differed) before
re-registering tests/test_pii_structural_gate.py in T-1411's scope.

### Changed
```
 src/frob/gates/_pii_structural/_keywords.py | 112 ++++++++++++++++++----
 tickets.md                                  | 138 ++++++++++++++++++++++++++--
 2 files changed, 228 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_prose_comment_with_no_referenced_identifier_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_in_reference_form_naming_real_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_matching_in_scope_identifier_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_hash_inside_string_literal_is_not_treated_as_comment` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 418 warning(s), 689 waived
- error-findings: none (measured, zero errors)
