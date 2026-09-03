## Done report

windows-latest matrix leg in ci.yml made advisory (job-level continue-on-error: ${{ matrix.os == 'windows-latest' }}), citing T-3425/T-3076 in the workflow comment. ubuntu-latest/macos-latest are unchanged -- they still fail the workflow on a test failure. Documented the boundary in docs/design/windows-portability.md (new file) and docs/guides/release.md's what-green-means note under Decision 4. Added TestCiWindowsLegAdvisoryOnly to tests/unit/test_release_workflow_gate.py: MUST-FIRE asserts continue-on-error names only matrix.os == windows-latest; MUST-STAY-QUIET asserts the full 3-platform matrix is intact and no other step/leg carries its own continue-on-error. Removal of the advisory flag (once T-3076 reaches zero) should be an explicit T-3076 acceptance line, not edited into this ticket.

### Changed
```
 .github/workflows/ci.yml                 | 13 ++++++
 docs/design/windows-portability.md       | 71 ++++++++++++++++++++++++++++++++
 docs/guides/release.md                   |  2 +
 tests/unit/test_release_workflow_gate.py | 47 +++++++++++++++++++++
 tickets/T-3425/ticket.md                 | 16 +++++--
 5 files changed, 146 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_build_job_continue_on_error_is_windows_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_matrix_still_includes_all_three_platforms` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_no_step_level_continue_on_error_smuggled_onto_other_legs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 11 error(s), 3959 warning(s), 858 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3425, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
