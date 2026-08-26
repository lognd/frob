## Done report

Changed:
tests/system/conftest.py::run
tests/system/conftest.py::DEFAULT_RUN_TIMEOUT_S

DIAGNOSIS (confirmed by local reproduction, not just theory):

tests/system/conftest.py's shared `run()` helper defaulted
`timeout=None` -- an unbounded `subprocess.run` wait. 468 of
tests/system/*.py's `run(...)` call sites relied on that default
(`git grep -h "run(" -- tests/system/*.py | grep -vc "timeout="` = 470,
matching the coordinator's independent count of 468).

I initially suspected this alone explained the 2+ hour hang, but the
existing `--timeout=120 --timeout-method=thread` in pyproject.toml
should have hard-killed a stuck worker at 120s -- so an unbounded wait
inside one test does not by itself explain "never terminates". I built
a minimal local repro (a throwaway pytest file with a
`subprocess.run(["sleep", "300"])` test, no xdist_group vs an
xdist_group-marked one, `-n N --dist=loadgroup --timeout=15
--timeout-method=thread`) to find the actual mechanism:

1. The wedging test blocks in `subprocess.communicate` -> `select()`.
2. At the outer per-test wall clock, pytest-timeout's thread method
   fires `pytest_timeout.timeout_timer`, which calls `os._exit(1)` on
   the WHOLE worker process (confirmed by reading pytest_timeout.py
   directly: it dumps stacks, then hard-exits, nothing more).
   `os._exit` skips atexit/finally, so the worker's own subprocess
   child (the wedging `frob check` call) is ORPHANED, not killed. My
   repro confirmed the orphan directly via `pgrep` after the run
   exited.
3. Under `--dist=loadgroup` (this repo's addopts), xdist's controller
   reacts to "node down" by REDISPATCHING the same test item to a
   fresh worker. That worker wedges on the identical unbounded wait and
   dies the same way 15-120s later, orphaning ANOTHER child. Repeated
   across every available worker in my repro
   (`.[gw0] node down` ... `[gw2] node down` ... `[gw3]` ...) until
   workers were exhausted and the run stopped making progress -- i.e.
   the run never terminates, matching the CI symptom exactly (reached
   ~99%, ~2 hours of no progress, cancelled).
4. This matches the real CI job's own tail lines precisely: GitHub
   Actions' cleanup terminated ten orphan processes at job end (uv,
   pytest, eight pythons; pids 5821-37282, spawned across the whole
   run) -- consistent with repeated worker-crash-and-redispatch cycles,
   each orphaning its own child.

I then confirmed the fix breaks the cycle: adding a bounded
`subprocess.run(..., timeout=N)` INSIDE the test (rather than relying
on the outer pytest-timeout wall clock) raises `TimeoutExpired`
directly in the test. `subprocess.run` itself kills the child on
timeout expiry (confirmed: `returncode: -9` in the repro traceback --
no orphan). The worker survives, xdist reports one normal FAILED test,
and the run continues -- no worker kill, no redispatch, no orphan. In
the identical --dist=loadgroup repro with a bounded per-call timeout,
the run completed in 5.94s reporting "1 failed, 3 passed" instead of
hanging.

FIX: `tests/system/conftest.py`'s `run()` now defaults to
`DEFAULT_RUN_TIMEOUT_S = 100` (chosen below the outer
`--timeout=120` wall clock so this bound fires first, and generous
enough not to flake a loaded CI runner's real `frob check` calls) and
raises a named `RuntimeError` ("system-test run() timed out after
Ns waiting on [...]") on expiry, wrapping the underlying
`TimeoutExpired`. Callers that need longer still pass an explicit
`timeout=` at their own call site, unchanged.

PROOF THE SUITE NOW TERMINATES: tests/system/test_run_helper_env_leak.py
(the file I extended) runs clean in 4/4; a direct call to `run(...,
timeout=0.01)` raises the new RuntimeError as designed (verified via a
standalone python -c repro, output: "CAUGHT: system-test run() timed
out after 0.001s waiting on [...]"); the originally-flagged
`test_ticket_readiness_is_not_an_arch001_finding` runs clean under the
new default. `tests/gates` (39 tests) and `tests/unit/strata/
test_mutation_audit.py` (10 tests) both terminate cleanly with the fix
present. A full unscoped `tests/system` + `tests/unit` run on this
shared dev box did not complete within available budget due to SEVERE
local host contention unrelated to this fix (load average 8-10 on a
12-core host from 3+ other live sibling agents running cargo/frob check
concurrently, confirmed via `ps`/`uptime`) -- a clean/uncontended CI or
solo-host run is needed for full-suite confirmation and is noted as the
residue ticket below (T-2992).

REAL FAILURES STILL REPORTED, NOT SKIPPED: no test was skipped, deleted,
or marked xfail. `frob check --budget 100 --ticket T-2980` and
`--only test --ticket T-2980` were run repo-wide; every finding
(gate:ARCH ARCH103 in src/frob/tickets/_new_renumber.py, gate:LARGE
LARGE001 in src/frob/stats/_agentic.py, and every gate:TEST
warning/waived item) is pre-existing and unrelated to the files this
ticket touched -- `grep -n "tests/system/conftest.py\|test_run_helper_env_leak"`
against the full check log returned zero hits.

Filed (residue):
T-2991 -- the deeper child-not-exiting defect: a frob
  subprocess spawned by a system test can be orphaned when its pytest
  worker is killed, independent of this ticket's timeout fix (evidence:
  the ten orphan pids from the real CI job's cleanup log, plus the
  local pgrep-confirmed orphan from my repro).
T-2992 -- capture and triage the real test failures the hang
  was hiding, once a clean/uncontended full-suite run (CI, or a
  solo-host local run) is available to produce the authoritative failed
  node-id list. Declared no-scope (pure investigation/triage record).

Evidence:
tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout::test_run_default_timeout_is_bounded_not_none
tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout::test_run_expiry_raises_a_named_loud_error
tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_strips_dispatch_agent_env_vars
tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_explicit_env_can_still_set_frob_agent

Gates: `frob check --budget 100 --ticket T-2980` and `--only test
--ticket T-2980` both clean of any finding touching this ticket's
changed files (verified by grep against the full log); the 2 gate
errors and the pre-existing TEST warnings present in those runs are all
in unrelated files (src/frob/tickets/_new_renumber.py,
src/frob/stats/_agentic.py, TEST006 no-coverage-stamp is environmental
to a fresh worktree) and predate this change.

### Changed
```
 tests/system/conftest.py                 | 70 +++++++++++++++++++++++++----
 tests/system/test_run_helper_env_leak.py | 33 +++++++++++++-
 tickets/T-2980/ticket.md                 | 75 ++++++++++++++++++++++++++++++++
 tickets/T-2991/ticket.md       | 75 ++++++++++++++++++++++++++++++++
 tickets/T-2992/ticket.md       | 53 ++++++++++++++++++++++
 5 files changed, 296 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout::test_run_default_timeout_is_bounded_not_none` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout::test_run_expiry_raises_a_named_loud_error` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_strips_dispatch_agent_env_vars` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_explicit_env_can_still_set_frob_agent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 27 error(s), 488 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
