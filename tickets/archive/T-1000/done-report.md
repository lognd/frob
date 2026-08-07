## Done report

Churn item 1 (docs/audits/coordination-churn.md#1): every post-close touch
staled the recap and `land` refused with ClaimDivergence even when the
fresh count strictly improved, forcing an identical manual
`frob ticket done-report` + re-land cycle each time (~10 occurrences).

`_reverify_test_count_claim` now compares both the test-count and
evidence-count halves of the captured claim against the fresh post-merge
numbers: an exact match is unchanged (no-op); a genuine REGRESSION (either
count now lower than recorded) still refuses with `ClaimDivergence`
exactly as before; a STRICT IMPROVEMENT (both counts `>=` recorded, at
least one strictly greater) now auto-accepts instead of refusing, and
`_rewrite_claims_section` rewrites the ticket's `### Captured claims`
Done-report block in the worktree ledger to the fresh numbers before the
land commit is made, so the landing commit itself carries the corrected
recap. Any evidence that is genuinely failing post-merge is refused
earlier, upstream in `_reverify_evidence_post_merge` (D-05), before this
claims check ever runs -- this ticket's acceptance direction for "any
failing test still refuses" is exercised there, unchanged.

### Changed
```
 src/frob/tickets/_land.py | 126 ++++++++++++++++++++++++++++++++++++++++------
 tests/test_ticket_land.py |  46 +++++++++++++++++
 tickets.md                |   3 +-
 3 files changed, 159 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_strictly_improved_test_count_auto_accepts_and_rewrites_recap` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_lower_gate_error_count_than_claim_still_lands` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4911 warning(s), 322 waived
- error-findings: DOC001@docs/audits/coordination-churn.md
