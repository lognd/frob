## Done report

SEC110 dispositioned on tests/helpers/bash.py ProgramFiles read via frob:waive, matching the repo's existing non-secret-env-read pattern

### Changed
```
 tickets/T-4458/ticket.md | 4 ++++
 1 file changed, 4 insertions(+)
```

### Evidence
- `tests/unit/test_helpers_bash.py::test_non_windows_returns_plain_bash` (pytest node id, verified passing when recorded)
- `tests/unit/test_helpers_bash.py::test_prefers_git_bash_over_system32_stub` (pytest node id, verified passing when recorded)
- `tests/unit/test_helpers_bash.py::test_system32_stub_only_skips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4799 warning(s), 965 waived
- error-findings: none (measured, zero errors)
