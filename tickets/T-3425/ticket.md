---
id: T-3425
title: 'CI: windows-latest job is advisory (continue-on-error) until the T-3076 Windows-only
  failure set is drained'
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- docs/design/windows-portability.md
- docs/guides/release.md
- tests/unit/test_release_workflow_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a push to main where only windows-latest fails, when ci.yml completes,
    then the workflow conclusion is success and verify_release_ci_status.py resolves
    GREEN
  evidence: []
- text: given a push where ubuntu-latest or macos-latest fails, when ci.yml completes,
    then the workflow conclusion is failure
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33277131782 (HEAD bb5c28203, 2026-08-29):
the windows-latest job fails at ~2% of the suite with
`SUITE-RESULT: DID-NOT-COMPLETE exitstatus=2 (INTERRUPTED) collected=12655`
and 4 failures before the interrupt; the previous run (33169097371)
completed with 24 failures. T-3076 characterized 278 Windows-ONLY failures
rooted in five missing POSIX primitives (fcntl, os.sysconf, AF_UNIX, fork
context, charmap codec). That burn-down is an epic-sized effort
(T-2963 daemon transport, T-3076 characterization), not a gate we can hold
a release on today.

CONSEQUENCE TODAY: ci.yml's overall conclusion is RED on every push
regardless of ubuntu/macOS health, so `scripts/verify_release_ci_status.py`
(T-3251) can never resolve GREEN and every release needs the
override_red_ci escape hatch -- which makes the escape hatch the normal
path and destroys its audit value.

DECISION (PLATFORM001 doctrine: declare the boundary, never silently degrade):
make the windows-latest job ADVISORY -- `continue-on-error: true` on that
matrix leg only -- with a comment block citing this ticket and T-3076, so
the job still runs and reports on every push (the signal is kept, and the
burn-down can be measured against it), but it no longer flips the
workflow conclusion. Document the boundary in docs/design/windows-portability.md
and docs/guides/release.md ("what green means"). Remove the advisory flag
when T-3076's set reaches zero -- add that as an explicit acceptance line
on T-3076 (do not edit T-3076's body from this ticket; note it in the Done
report for the coordinator).

ALSO record (do not fix here, file under T-3076 if not already covered)
the 4 concrete failures from run 33277131782:
  tests/gates/test_comment_placement.py::TestCplace001::test_symref_binds_to_the_enclosing_function
     assert 'src\\frob\\x.py::handler' == 'src/frob/x.py::handler'  (symref uses os.sep, must be posix)
  tests/gates/test_comment_placement.py::TestCplace001/002::test_must_stay_quiet_exempt_path (same path-shape cause)
  tests/system/test_ci_hang_guard_positive_control.py::...::test_ordinary_fast_test_is_unaffected
     shells to `timeout` which on Windows is timeout.exe ("Invalid syntax. Default option is not allowed more than '1' time(s)")

MUST-FIRE FIXTURE:   tests/unit/test_release_workflow_gate.py (or a sibling) asserts that
                     ONLY the windows-latest leg carries continue-on-error, never ubuntu/macOS.
MUST-STAY-QUIET:     the ubuntu and macOS legs still fail the workflow on a test failure.
