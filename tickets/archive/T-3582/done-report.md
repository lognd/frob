## Done report

Root cause: T-3577's win32-bounded-communicate/taskkill fix only lives in
tests/system/conftest.py::run. tests/integration/*.py (test_gitlog.py,
test_exports_write.py, test_fleet_integration.py, test_interfaces.py,
test_mutate_runner.py) had 13 raw subprocess.run call sites with NO
timeout at all -- the exact "hangs forever, no bound" shape T-2980
invented DEFAULT_RUN_TIMEOUT_S to close for tests/system/, never applied
to tests/integration/. Run 33385515507 (HEAD 94931dde1) died with
KeyboardInterrupt at [1%] on windows-latest, serial collection position
~130, inside tests/integration/test_gitlog.py territory -- consistent
with an unbounded subprocess.run hang there, not a repeat of T-3577's
fixed hazard.

Fix:
(a) added a persistent (not T-3560-temporary) -v --full-trace to the
    windows-latest Test step in .github/workflows/ci.yml, staying until
    the leg is green.
(b) added tests/conftest.py::run_bounded_subprocess -- the shared,
    always-timeout-bounded home for tests/integration/'s git/frob
    subprocess helpers, mirroring tests/system/conftest.py::run's win32
    branch (bounded Popen.communicate + taskkill /T /F on expiry, no
    untimed post-timeout retry). Routed all 13 call sites across the 5
    files through it.

Evidence:
- uv run pytest -p no:xdist tests/integration/{test_gitlog,
  test_exports_write,test_fleet_integration,test_mutate_runner,
  test_interfaces}.py -q -k "not deploy": 45 passed (3x rerun clean;
  test_deploy_generate_writes_and_checks/test_deploy_malmberg_pilot.py
  excluded -- pre-existing worktree gap, strata_core native extension not
  built here, reproduces identically on main/HEAD with the exact same
  file unchanged)
- uv run ruff check tests/conftest.py + the 5 touched integration files:
  clean
- uv run frob check --only drift (scoped read): the new frob:tests
  directive on run_bounded_subprocess resolves; zero DRIFT002 findings
  for tests/conftest.py or tests/integration/ after the fix (an earlier
  pass with the wrong nodeid separator, `::` instead of `.` between class
  and method, was caught and corrected here)

Filed: none (this ticket itself was filed by the coordinator; no further
splits needed)

Gates: frob check --only drift clean of anything in this diff's scope;
this is a test-infra-only change (frob:no-behavior-change) so BUG002's
designated-evidence-must-PASS-at-parent check applies, not the normal
fails-at-main shape

### Changed
```
 .github/workflows/ci.yml                    | 12 +++-
 tests/conftest.py                           | 86 +++++++++++++++++++++++++++++
 tests/integration/test_exports_write.py     | 13 +++--
 tests/integration/test_fleet_integration.py | 24 ++++----
 tests/integration/test_gitlog.py            | 21 +++----
 tests/integration/test_interfaces.py        | 22 +++++---
 tests/integration/test_mutate_runner.py     | 15 ++---
 tickets/T-3582/ticket.md                    | 13 ++++-
 8 files changed, 159 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/integration/test_gitlog.py::TestGitlogGrouping::test_features_grouped_separately` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 28 error(s), 4125 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_conftest_sigbreak_faulthandler.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_conftest_sigbreak_faulthandler.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3582, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
