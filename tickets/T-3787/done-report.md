## Done report

Added an OPTIONAL land target branch to frob ticket land. The pipeline already published onto and resynced root's CURRENT checked-out branch (main was never hardcoded as the land target); the one genuinely hardcoded main was the LAND-PROOF ancestry check. New: --branch/--onto NAME plus a ticket_land_branch config default (settable as [tool.frob] ticket_land_branch in pyproject.toml so post-alpha work defaults off a frozen main). _resolve_land_target_branch validates the target exists and equals root's current branch (else LandError.TargetBranchInvalid). The resolved target rides on LandReport.target_branch so LAND-PROOF verifies ancestry against the real target. Default (None) path is byte-identical to before. Landing onto a branch root is not checked out on is deferred (needs CAS base/resync/drift-guard re-pointing).

### Changed
```
 tickets/T-3787/ticket.md | 29 ++++++++++++++++++++++++++++-
 1 file changed, 28 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/ticket_land_suite/test_land_target_branch.py::TestLandOntoNonMainBranch::test_real_land_onto_dev_lands_on_dev_not_main` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_target_branch.py::TestDefaultTargetUnchanged::test_default_land_targets_main_and_reports_main` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_target_branch.py::TestTargetBranchRefusals::test_missing_target_branch_refuses` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_target_branch.py::TestTargetBranchRefusals::test_target_branch_root_is_not_on_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 4461 warning(s), 924 waived
- error-findings: DOC006@tickets/T-3807/ticket.md
