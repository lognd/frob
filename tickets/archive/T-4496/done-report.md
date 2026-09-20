## Done report

Set [tool.frob] ticket_land_branch = dev and dev_version_bump = true in pyproject.toml, added dev to ci.yml push branches, and documented the branch flow (main frozen at the released commit, dev is the land target, fast-forward main at each sprint cut) in docs/guides/release.md. Evidence: tests/unit/test_dev_branch_workflow.py parses the live pyproject.toml and ci.yml. Found while doing it: frob ticket work creates worktrees from a literal main, and evidence/done-report --base-ref default to main; filed as T-4492.

### Changed
```
 .github/workflows/ci.yml               |  2 +-
 docs/guides/release.md                 | 18 ++++++++++++
 pyproject.toml                         | 20 ++++++++------
 tests/unit/test_dev_branch_workflow.py | 50 ++++++++++++++++++++++++++++++++++
 tickets/T-4496/ticket.md     | 22 ++++++++++++---
 5 files changed, 98 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_dev_branch_workflow.py::test_land_target_is_dev` (pytest node id, verified passing when recorded)
- `tests/unit/test_dev_branch_workflow.py::test_ci_runs_on_dev_and_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_dev_branch_workflow.py::test_dev_version_bump_is_on` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4889 warning(s), 967 waived
- error-findings: none (measured, zero errors)
