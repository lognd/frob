## Done report

Fixed windows CI diag round 9's two defects. (1) pwsh runs steps with
$ErrorActionPreference='Stop' by default, promoting a native command's
first stderr line into a terminating error -- this killed rounds 7, 8
and 9 (uv chatter, then frob's own gitio WARNING). Set Continue as the
step's first line. (2) the fixture repo was git init with zero
commits, so frob's own gitio git rev-parse HEAD failed rc=128 and frob
aborted with "frob: interrupted" before its own diagnostics ran; added
one empty commit right after git init.

Also filed T-3620 (low priority, out of scope here) for the underlying
gitio behavior: a commitless repo's rev-parse HEAD failure surfaces as
a generic "frob: interrupted" instead of a clear NoCommitsYet-shaped
error -- still reachable by any real caller, not just this CI fixture.

Evidence: tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_step_sets_error_action_preference_continue_first
and ::test_diag_fixture_repo_has_an_initial_commit (both new). Full
tests/test_ci_workflow_matrix.py run: 14/14 pass.

Filed: T-3620.

### Changed
```
 .github/workflows/ci.yml         |  2 ++
 tests/test_ci_workflow_matrix.py | 53 ++++++++++++++++++++++++++++++++++++++--
 tickets/T-3619/ticket.md         |  3 +++
 3 files changed, 56 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_step_sets_error_action_preference_continue_first` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_fixture_repo_has_an_initial_commit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 13 error(s), 4128 warning(s), 902 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3619, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
