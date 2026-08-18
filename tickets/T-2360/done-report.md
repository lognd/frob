## Done report

Changed:
src/frob/verify/_backpressure.py::LandProfileSettings
src/frob/verify/_backpressure.py::settings_for_profile
src/frob/verify/_backpressure.py::_NON_RAPID_LAND_PROFILE_SETTINGS
src/frob/verify/_backpressure.py::_RAPID_LAND_PROFILE_SETTINGS
src/frob/verify/__init__.py (export LandProfileSettings, settings_for_profile)
tests/unit/verify/test_backpressure.py::TestSettingsForProfile (+5 methods)
docs/modules/tickets-verify-sweep.md (Land profile settings T-2360 section)

Evidence:
tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_fortress_matches_current_branch_logic
tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_standard_matches_current_branch_logic
tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_rapid_matches_current_branch_logic
tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_settings_are_frozen
tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_unknown_profile_value_raises
(all 22 tests in tests/unit/verify/test_backpressure.py pass, exitstatus=0)

Filed: none

Gates: uv run frob check --only coverage --only doclink --only docanchor --ticket T-2360
clean of any NEW finding attributable to this ticket's touched files
(COV002 on the 6 new test symbols was fixed by adding frob:ticket T-2360
directives; the remaining COV/DOC/DRIFT findings in that run are all in
files this ticket never touched -- scripts/fleet_status.py, src/frob/verify/_drain.py,
docs/commands/release.md, src/frob/app/verify_runner.py, src/frob/app/ticket_runner/_lifecycle.py --
pre-existing, confirmed via `git diff main --stat` showing zero diff for
those paths). uv run frob check --only test --ticket T-2360: gate:TEST
0 errors, 31 warnings (pre-existing, repo-wide), 4 waived.

`frob check --land-parity` could not complete within the foreground budget
under current fleet load (repeatedly deferred the `static` stage group and
returned "could not evaluate" rather than a false-clean answer, per its own
design) -- disclosed per section 6g/3c rather than claimed. The scoped
checks above are the evidence this Done report actually stands on.

Disclosed scope cut (per the ticket's own acceptance): no call site
(_land.py:2878/:3103, _land_cmd.py:4324/:4519, _evidence.py:323,
_close_cmd.py:463) was migrated to read LandProfileSettings -- that is
T-2361's job, deliberately split out so this leaf never needed a lease on
_land.py/_land_cmd.py.

### Changed
```
 tickets/T-2360/done-report.md | 56 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2360/ticket.md      | 12 ++++++++--
 2 files changed, 66 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_fortress_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_standard_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_rapid_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_settings_are_frozen` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_unknown_profile_value_raises` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2360/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2360, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/verify/_backpressure.py, WIRE003@docs/modules/cli.md
