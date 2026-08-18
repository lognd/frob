## Done report

Fixed the WIRE001/WAIVE008 inconsistency directly: WIRE001's own
`_new_callable_records` (src/frob/gates/_wire.py) now excludes a
pydantic `@field_validator`/`@model_validator` via `_is_pydantic_
validator` (frob.gates._dead_symbols, T-1652), the exact same dynamic-
dispatch rescue it already applied for an autouse pytest fixture
(`_is_autouse_pytest_fixture`, T-1510) -- closing the gap WAIVE008's own
`_wire001_symbol_now_rescued` helper had already assumed was closed.

Added tests/unit/test_wire001_pydantic_validator_rescue.py (kept
separate from tests/test_gates.py::TestWireGate, whose file I did not
want to risk another lease collision on): a fresh `@model_validator`
and a fresh `@field_validator` each prove the rescue (must-fail-first,
manually verified: reverted src/frob/gates/_wire.py to its pre-fix
state via a scratch copy -- git stash is repo-global and blocked by
this repo's own guard hook, so used `git checkout --`/restore-from-
scratch-copy instead -- re-ran the 3-test file, confirmed both new
tests genuinely FAIL against the unfixed gate logic, restored the fix,
confirmed all 3 pass again). A third test is the must-still-pass
positive control: an ordinary new function with no pydantic decorator
still fires WIRE001, proving the fix narrows the false positive rather
than disabling the gate. `frob ticket evidence --check-repro` could not
be used for the automated verdict here -- it is a pre-land-only
mechanism per docs/modules/tickets.md#check-repro-post-land-limitation-
t-2025 (no commit yet exists with the test present but the fix absent
in this worktree's own history at the point I ran it); the manual
revert-and-rerun above is the equivalent verification.

Also documented the two rescue predicates together for the first time
in docs/modules/gates.md's WIRE001/WIRE002 section (a "Dynamic-dispatch
rescues" subsection) -- T-1510's autouse-fixture rescue had never been
documented there at all, a pre-existing gap I closed while already
touching this exact code path.

Re-measured `uv run frob check --only docblocks --json`: 1 error
remains, the T-2330-deferred `_drain.py` DRIFT002 finding tracked
separately as T-2337 (blocked on T-2324) -- unrelated to this ticket.

### Changed
```
 tickets/T-2325/ticket.md | 18 ++++++++++++++++--
 1 file changed, 16 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_model_validator_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_field_validator_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_ordinary_new_function_still_flagged_positive_control` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2325, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md
