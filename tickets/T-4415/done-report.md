## Done report

ci.yml: the build job's self-gate step is declared (in-file comments and a job-level permissions block) the unscoped full-sweep source of truth; a push-only step files a regression ticket attributed to the commit range since the last green run and pushes it back to the branch (contents: write is the narrowest grant; PR runs never push). docs/modules/tickets-landing.md and docs/guides/release.md carry the statement: land proves the diff, CI proves the repo. Evidence: tests/unit/test_ci_self_gate_unscoped.py parses the live workflow and docs, bound per criterion. Ticket-scoped frob check skipped by coordinator decision (fleet load); the land's own check is the gate. Implementer session was terminated by a login expiry after binding evidence; Done report written by the coordinator from the worktree commits.

### Changed
```
 .github/workflows/ci.yml                 | 105 +++++++++++++++++
 CHANGELOG.md                             |   3 +
 docs/guides/release.md                   |  19 ++++
 docs/modules/tickets-landing.md          |  40 +++++++
 tests/unit/test_ci_self_gate_unscoped.py | 189 +++++++++++++++++++++++++++++++
 tickets/T-4415/done-report.md            |  20 ++++
 tickets/T-4415/ticket.md                 |  15 ++-
 7 files changed, 388 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateIsUnscoped::test_self_gate_documented_as_unscoped_authority` (pytest node id, verified passing when recorded)
- `tests/unit/test_ci_self_gate_unscoped.py::TestLandVsCiDocumentedSplit::test_both_doc_homes_state_the_split` (pytest node id, verified passing when recorded)
- `tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateRegressionFiling::test_filing_step_reuses_finding_filing_path_not_a_new_implementation` (pytest node id, verified passing when recorded)
- `tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateRegressionFiling::test_filing_step_attributes_to_a_commit_range` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
