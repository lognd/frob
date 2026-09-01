## Done report

Repointed 5 stale tests/test_gates.py::Class doc citations in docs/modules/gates.md (TestSeverityOverrides, TestWaive004DegradedRunGuard x2, TestWaive004ExaminedSitesGuard, TestFixEngineTierA) to their tests/gates_suite/ homes after T-3586's split. Re-measured this sweep's other 2 identities live: DOC006 was already 0 for docs/design/check-fix-engine.md and docs/design/macos-portability.md (no test_gates.py text present) before this ticket started; COV008 (diff-scoped to the split's own moment) does not reproduce in a static check post-land. Verified with frob check --only docblocks: 0 DOC006 findings repo-wide.

### Changed
```
 docs/modules/gates.md    | 10 +++++-----
 tickets/T-3630/ticket.md | 23 +++++++++++++++++++++--
 2 files changed, 26 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 13 error(s), 4264 warning(s), 903 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3630, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
