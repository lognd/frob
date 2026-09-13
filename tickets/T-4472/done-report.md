## Done report

Changed:
.github/workflows/release.yml::jobs.build (Install the just-built wheels into a clean venv and import them -- venv creation + uv pip install moved inside the non-cross arm)
tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke.test_install_only_runs_inside_the_non_cross_branch

Evidence (frob:tests T-4472):
tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_install_only_runs_inside_the_non_cross_branch
Full file: pytest tests/unit/test_release_workflow_gate.py -q -p no:randomly -> 38 passed
YAML validated with python yaml.safe_load

Filed: none

Gates: frob check --ticket T-4472 clean against scope after sweep (2
pre-existing out-of-scope findings remain -- DRIFT001 on
src/frob/doctor.py and REF002 on docs/design/macos-portability.md --
neither touched by this ticket's diff). BUG002 waived via frob ticket
body --append-file: --check-repro reported TEST_ABSENT_AT_PARENT (test
written for this ticket, does not exist at the ticket-start parent by
construction) plus this being a CI-config change with no local
fail-before/pass-after execution path; citing release run 34786316434.

Root cause confirmed: uv pip install of the foreign-arch wheel ran
UNCONDITIONALLY before the matrix.cross if-branch, so the cross-skip
added in T-4470 was never reached -- the install itself failed first
("Failed to determine installation plan ... incompatible with the
current platform"). Fix moves venv creation + install inside the
non-cross (native) arm; cross entries now do only a wheel-existence
check via ls.

### Changed
```
 .github/workflows/release.yml            | 42 ++++++++++++++--------
 tests/unit/test_release_workflow_gate.py | 62 ++++++++++++++++++++++++++++++++
 tickets/T-4472/ticket.md                 | 14 ++++++++
 3 files changed, 103 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_install_only_runs_inside_the_non_cross_branch` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4805 warning(s), 965 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md
