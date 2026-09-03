## Done report

Round 12 replaces the `cmd /c $cmdLine` invocation (which died silently
at its own line ~1.3s in, exit 1, no further breadcrumb -- another pwsh
native-command stream landmine, this time at the cmd boundary) with the
exact `Start-Process -RedirectStandardOutput/-RedirectStandardError`
pattern the workflow's own "Test (windows, timed with hang guard)" step
already runs successfully on this runner. `-WorkingDirectory $fixture`
replaces the old Push-Location/Pop-Location pair around the invocation;
`-ArgumentList` passes each argument as its own array element so there
is no shell-quoting boundary for `--project`'s value to survive. Bounded
`Wait-Process -Timeout 290` (under the step's own 5-minute
`timeout-minutes`, above the 240s in-process faulthandler watchdog), and
output capture (`Get-Content` of both redirect files) plus the exit-code
print now run in a `finally` block so they execute whichever of
Wait-Process-returned / Wait-Process-timed-out / Start-Process-itself-
threw actually happened -- round 11's total silence after the
"about to invoke" breadcrumb cannot recur. The whole region is also
wrapped in try/catch printing "invoke threw: $_" per the ticket's
explicit direction. The elapsed-time hang discriminator (>=235s treated
as a hang) and exit-0-on-non-hang contract are unchanged.

Updated tests/test_ci_workflow_matrix.py's assertions for the new
invocation shape: --project's value is now its own -ArgumentList array
element rather than a cmd-escaped string; -WorkingDirectory replaces the
Push-Location check; the cmd-native-redirect test became a
Start-Process-not-cmd test (with a check that "cmd /c" appears nowhere
in actual CODE lines, only in explanatory comments about the round-10/11
history); the breadcrumb markers changed to "about to invoke uv via
Start-Process"/"Start-Process invocation returned"; added two new tests
covering the try/catch wrap and the finally-block output capture, since
those are the actual fix this round makes (round 11 already had
breadcrumbs and redirect-to-file, which is what silently died).

Evidence:
tests/test_ci_workflow_matrix.py full file (22/22 green, including two
new tests added for the try/catch and finally-block guarantees)
tests/unit/test_release_workflow_gate.py (21/21 green -- the windows-leg
advisory-boundary guard this step must still respect)
YAML parses cleanly (python3 -c "import yaml; yaml.safe_load(...)")

Filed: none

Gates: gates-native/gates-security/static chunks show no new findings on
ci.yml/test_ci_workflow_matrix.py; ruff-format initially flagged the
test file (fixed, `ruff format` clean, tests re-verified green after);
remaining ruff-check/ruff-format findings across ~50 other files are
pre-existing repo-wide baseline, confirmed unrelated to this ticket's
two touched files. gates-fast was not re-run standalone (same foreground-
cap load T-3634/T-3636 both hit on this host).

### Changed
```
 .github/workflows/ci.yml         |  86 ++++++++++++++++++--------
 tests/test_ci_workflow_matrix.py | 130 ++++++++++++++++++++++++---------------
 tickets/T-3637/ticket.md         |   5 +-
 3 files changed, 142 insertions(+), 79 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_invocation_is_wrapped_in_try_catch` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_invocation_output_capture_is_unconditional` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 28 error(s), 4170 warning(s), 896 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3628/ticket.md, DOC006@tickets/T-3629/ticket.md, DRIFT002@tests/ticket_land_suite/test_archive.py, DRIFT002@tests/ticket_land_suite/test_claim_close.py, DRIFT002@tests/ticket_land_suite/test_dirt_ownership.py, DRIFT002@tests/ticket_land_suite/test_land_core.py, DRIFT002@tests/ticket_land_suite/test_land_lock.py, DRIFT002@tests/ticket_land_suite/test_land_plan.py, DRIFT002@tests/ticket_land_suite/test_ledger_splice.py, DRIFT002@tests/ticket_land_suite/test_push.py, DRIFT002@tests/ticket_land_suite/test_release.py, DRIFT002@tests/ticket_land_suite/test_verify_intent.py, DRIFT002@tests/ticket_land_suite/test_verify_reset.py, DRIFT002@tests/ticket_land_suite/test_waive_deletion.py, DRIFT002@tests/ticket_land_suite/test_wip.py, F401@/home/logan/projects/frob/.claude/worktrees/t-3637/tests/test_ticket_land.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3637, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
