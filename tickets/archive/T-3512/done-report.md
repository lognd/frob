## Done report

removed T-3425 advisory flag now that all three CI legs are green (run 34758499278)

### Changed
```
 tickets/T-3076/ticket.md | 21 ++++++++++++++++++++-
 tickets/T-3512/ticket.md | 21 +++++++++++++++++++++
 2 files changed, 41 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_matrix_still_includes_all_three_platforms` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_no_step_level_continue_on_error_smuggled_onto_other_legs` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_build_job_continue_on_error_is_windows_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4810 warning(s), 964 waived
- error-findings: REF002@docs/design/macos-portability.md
