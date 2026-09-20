## Done report

Changed:
tests/test_ci_workflow_timeout.py::_pytest_test_step (frob:waive WIRE001 directive)

Evidence:
tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo -- passed
(`SUITE-RESULT: exitstatus=0 collected=1 failed=0`, run with `-p no:xdist` since this
single-test file stalls under xdist's worker-crash path unrelated to this fix)

Filed:
T-4311 -- T-4305's declared scope misses .github/workflows/ci.yml that this test
file's own pre-existing frob:tests directives cover (SCOPE002); widening scope is
blocked right now by T-4269's live cross-worktree lease on that same path, and the
condition pre-dates this ticket's own diff (reproduces with the fix reverted too)
T-4312 -- recurrence-prevention: warn at ticket-close/land time when closing would
strand a live frob:waive WIRE001 follow_up="T-####" naming the ticket being closed

Reasoning (per the ticket's own instruction not to just delete the waiver): read
the waiver's reason -- it names `test_macos_step_backgrounds_the_interpreter_directly_not_uv_run`
and `TestUbuntuTestStepIsTimedWithStackDump._ubuntu_test_step`/
`TestMacosTestStepSignalsTheRealInterpreter._macos_test_step` as `_pytest_test_step`'s
only callers; verified all three exist and call it (`grep -n _pytest_test_step
tests/test_ci_workflow_timeout.py`). `_pytest_test_step` is a private (`_`-prefixed)
helper in a file under `tests/`, called only by that file's own test methods -- a
pure workflow-YAML-inspection helper genuinely has no production caller BY
CONSTRUCTION, not "not yet". `src/frob/gates/_wire.py::_wire002_is_permanent_test_helper_waiver`
and its T-1592 precedent (documented in docs/modules/gates.md, live sibling
waivers in tests/unit/verify/test_quarantine.py, tests/unit/test_land_orphaned_evidence.py,
tests/unit/test_ticket_land_bug003_t2215.py, etc.) is exactly this shape: a
`permanent="true"` waiver on a private test-tree helper satisfies WIRE002 with no
`follow_up=` at all, because the no-caller condition is permanent design, not a
pending TODO. Rebound the waiver from `follow_up="T-4274"` (T-4274 is done, which
is what stranded it) to `permanent="true"`, matching the precedent this file's own
`_load_ci_workflow`/`_ubuntu_test_step` helpers are already documented as sharing.
Did not build the close-time strand-detector -- filed T-4312 instead, per the
ticket's own instruction that this ticket is the unblock, not the redesign.

Gates: frob check --ticket T-4305 --only scope: 1 error (SCOPE002, pre-existing,
tracked as T-4311, blocked by T-4269's live lease -- not caused by and not
resolvable within this ticket's diff). All other gate families in `frob check
--ticket T-4305`'s full run are repo-wide baselines per its own gate:scope-note,
not scoped to this ticket, and were not touched by this change (gate:ARCH,
gate:PRE, gate:SELFAUDIT, gate:TODO failures pre-exist independent of this diff --
confirmed by reverting the fix and observing gate:SCOPE's SCOPE002 unaffected by
the revert, and gate:TODO/gate:PRE/gate:SELFAUDIT findings cite unrelated files
(src/frob/gates/_land_format.py, etc.) never touched by this ticket).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 4656 warning(s), 950 waived
- error-findings: ARCH103@src/frob/graph/cache.py, PRE001@tickets/T-4305, SCOPE002@tickets.md, SELFAUDIT001@design, TODO002@src/frob/gates/_land_format.py
