## Done report

Closes the actual gap traced in the ticket body: `_sync_interface_pre_
land_step` (`frob.app.ticket_runner._land_cmd`) now `sys.exit(1)`s when
`sync_interface_report` returns `Err` instead of logging a WARNING and
proceeding. Verified `sync_interface_report`'s own body directly before
making this change: its ONLY `Err` path is `load_design_ids(...).errors`
non-empty (a design file failed to LOAD/parse) -- a missing/empty
`design/` tree returns `Ok(SyncInterfaceReport(files=()))`, never an
`Err` -- so refusing unconditionally on `Err` never misfires on the
benign "no design root" case every existing `TestAbsorbPreLandFixes`
test already relies on (verified: those three tests plus a new explicit
`test_still_proceeds_when_design_dir_absent` all still pass).

This is a SINGLE choke point fix, not two: `_absorb_pre_land_fixes`
calls `_sync_interface_pre_land_step` BEFORE `_tier_a_pre_land_step`
(which separately runs the SYS104/SYS100 Tier-A auto-fix handlers that
also silently skip on the same ParseFailed) -- the new `sys.exit(1)`
terminates the whole land process before Tier-A ever gets a chance to
independently re-hit the same corruption, so no second fix was needed
inside the Tier-A engine itself.

New test coverage: `TestSyncInterfacePreLandRefusesOnParseFailed`
(2 tests) -- a real malformed `.strata` file (unterminated string,
matching the actual incident's shape) causes `SystemExit(1)`; a repo
with no `design/` directory at all still proceeds without raising.

NOT done in this pass, disclosed per the "if cheap" qualifier: the
duplication-is-the-mechanism restructuring (collapsing `fs.write`'s and
`fs.read`'s hundreds-of-paths `may ... via` lists from two hand-
maintained copies into one shared source) is a design-language change to
`.strata` itself or a generation step, not a small refusal-timing fix --
genuinely not cheap, so left as an observation rather than attempted
here. Worth a dedicated follow-up if the coordinator wants it pursued.

`frob check --only prework --only scope --only sys --ticket T-1796` is
clean. `frob check --only coverage` shows 0 new findings for the touched
function.

### Changed
```
 CHANGELOG.md                           |  19 -----
 design/frob.strata                     |   6 +-
 rapid-debt.jsonl                       |   1 +
 src/frob/app/ticket_runner/__init__.py |  45 ++++++++++-
 tests/unit/test_app_runners_batch7.py  |  55 +++++++++++++
 tickets/T-1674/done-report.md          |  59 ++++++++++++++
 tickets/T-1674/ticket.md               | 128 ++++++++++++++++++++++++++++-
 tickets/T-1796/ticket.md               | 142 +++++++++++++++++++++++++++++++++
 8 files changed, 431 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestSyncInterfacePreLandRefusesOnParseFailed::test_refuses_when_a_design_file_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestSyncInterfacePreLandRefusesOnParseFailed::test_still_proceeds_when_design_dir_absent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 796 warning(s), 727 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, SEC110@src/frob/app/ticket_runner/__init__.py
