## Done report

Changed the T-1366 coverage-stamp CI step and its two error-message
references to invoke 'uv run frob coverage --full' (preceded by
'frob ticket reconcile --apply' and 'frob doctor', replicating the
Makefile coverage target's exact recipe) instead of shelling to
'make coverage', which windows-latest never installs. Added
TestCoverageStepUsesFrobNotMake to tests/test_ci_workflow_matrix.py
(the repo's established frob:tests binding location for ci.yml
content assertions) asserting no CI step spells make coverage and
that the T-1366 step calls frob coverage --full directly. Scope
expanded via frob ticket scope --add (reasoned) to include that test
file since bug-kind tickets require pytest evidence node ids.

### Changed
```
 tickets/T-3077/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_does_not_shell_to_make` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_calls_frob_coverage_full` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 26 error(s), 4108 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3077, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
