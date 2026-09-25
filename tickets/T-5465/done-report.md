## Done report

CI run 35951365410 failed test_gate_stage_group_migration_is_byte_identical: _STAGE_GROUPS["gates-security"] gained an extra 'a11y' member versus the golden literal captured at T-4336's migration time. T-5323 legitimately added a11y (A11Y101-115) to _GATE_STAGE_GROUPS' gates-security bucket after that golden was taken; added 'a11y' to the golden. Post-merge, dev had also grown invariant_level and milestone_closure in gates-fast since the golden was regenerated, so those were added too. Also removed a self-referential frob:tests directive the test carried on itself. Verified against the whole TestCheckStageGroups class.

### Changed
```
 CHANGELOG.md                   |    3 +
 tests/system/test_cli_check.py |   13 +-
 tickets/T-5465/done-report.md  | 4425 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-5465/ticket.md       |   10 +-
 4 files changed, 4445 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_gate_stage_group_migration_is_byte_identical` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
