## Done report

Root cause (per coordinator's narrowing, run 33390218738 full-trace):
frob check ITSELF hangs on win32 -- the interrupt fires while conftest.py
run()'s proc.communicate(timeout=...) waits on the suite's FIRST
'python -m frob check' child (test_cli_check.py:67), not inside pytest's
own machinery. frob check plausibly has never completed on win32 at all
(standalone-install only ever runs 'frob --help').

Fix (diagnostics, not yet a confirmed root-cause fix -- no Windows box
available to reproduce interactively):
1. .github/workflows/ci.yml: new windows-only step before the Test step
   -- runs one bare frob check against a tiny fixture repo (reusing the
   standalone-install job's own fixture recipe) with faulthandler.
   dump_traceback_later armed INSIDE the child process, so a hang names
   the exact Python frame instead of only proving the outer process
   eventually died.
2. tests/system/conftest.py::run: both the win32 and POSIX
   TimeoutExpired branches now include the child's drained stdout/stderr
   in the raised RuntimeError (previously discarded on win32, never read
   at all on POSIX) -- every future hang carries its own diagnostic
   output instead of needing CI-log archaeology.

Investigated but NOT changed (candidates named in the brief): the
capability-ratchet/self-audit land-gate lock is not implicated (frob
check on a tiny fixture never reaches those code paths); the T-3506
portable_flock_acquire msvcrt blocking-acquire path is already bounded
by _MSVCRT_BLOCKING_ACQUIRE_CEILING_S (T-3577), so it raises rather than
hangs forever; _process_pool_start_method already falls back to 'spawn'
when forkserver is unavailable (win32). None of these read as an
unbounded hang by code inspection alone -- the diagnostic step above is
needed to actually name the frame on a real windows-latest runner.

Evidence:
- uv run pytest -p no:xdist tests/system/test_run_helper_env_leak.py:
  7 passed (POSIX TimeoutExpired path exercised on this runner, message
  now carries drained output)
- uv run pytest -p no:xdist tests/system/test_cli_check.py: 37 passed
- uv run ruff check tests/system/conftest.py: clean
- python3 -c "import yaml; yaml.safe_load(...)" on ci.yml: parses clean

Filed: none

Gates: ruff clean; existing run() test suite green; YAML parses; new
diagnostic step is additive/windows-only, does not gate any other job

### Changed
```
 .github/workflows/ci.yml | 61 ++++++++++++++++++++++++++++++++++++++++++++++++
 tests/system/conftest.py | 33 +++++++++++++++++++++++---
 tickets/T-3589/ticket.md | 13 ++++++++++-
 3 files changed, 103 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/system/test_run_helper_env_leak.py::TestRunHelperWin32TimeoutSurvivesAHungGrandchild::test_timeout_kills_process_tree_and_never_calls_an_untimed_communicate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 28 error(s), 4109 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@tickets/T-3587/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, DUP001@tests/system/conftest.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3589, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
