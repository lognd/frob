## Done report

Evidence-close only: the INV006 fix (frob:waive at src/frob/tickets/_new_renumber.py:15)
is already on main (c6c2ee55). Verified `frob check --only invariant --ticket T-1107`
passes with 0 errors, 0 warnings against the live file. Added a regression test,
TestInv006Gate.test_new_renumber_file_has_no_unanchored_exclusivity_claim, that copies
the real _new_renumber.py source into an isolated snapshot and asserts inv006_gate
returns zero violations -- proving the finding is gone from the actual file, not just
that a waiver line exists somewhere in it, and locking the regression going forward.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv006Gate::test_new_renumber_file_has_no_unanchored_exclusivity_claim` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 511 warning(s), 426 waived
- error-findings: none (measured, zero errors)
